# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import cv2
import socket
import threading
import queue
import pickle
import struct
import numpy as np
import json
from datetime import datetime
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
import select
import time

# 自定义扁平化风格
class FlatStyle:
    @staticmethod
    def configure_styles():
        style = ttk.Style()
        
        # 主框架样式
        style.configure('TFrame', background='#f5f5f5')
        
        # 按钮样式
        style.configure('TButton', 
                       foreground='#333333',
                       background='#e0e0e0',
                       borderwidth=0,
                       padding=6,)
        style.map('TButton',
                 foreground=[('pressed', '#ffffff'), ('active', '#333333')],
                 background=[('pressed', '#4CAF50'), ('active', '#f0f0f0')])
        
        # 标签样式
        style.configure('TLabel', 
                       background='#f5f5f5',
                       foreground='#333333',)
        
        # 输入框样式
        style.configure('TEntry',
                       fieldbackground='#ffffff',
                       foreground='#333333',
                       borderwidth=1,
                       relief='flat',
                       padding=5)
        
        # 组合框样式
        style.configure('TCombobox',
                       fieldbackground='#ffffff',
                       foreground='#333333',
                       selectbackground='#4CAF50',
                       selectforeground='#ffffff',
                       borderwidth=1,
                       relief='flat',
                       padding=5)
        
        # 标签框架样式
        style.configure('TLabelframe',
                       background='#f5f5f5',
                       foreground='#333333',
                       borderwidth=1,
                       relief='flat')
        style.configure('TLabelframe.Label',
                       background='#f5f5f5',
                       foreground='#4CAF50',)
        
        # 树视图样式
        style.configure('Treeview',
                       background='#ffffff',
                       foreground='#333333',
                       fieldbackground='#ffffff',
                       borderwidth=0,)
        style.map('Treeview',
                 background=[('selected', '#4CAF50')],
                 foreground=[('selected', '#ffffff')])
        
        # 滚动条样式
        style.configure('Vertical.TScrollbar',
                       background='#e0e0e0',
                       troughcolor='#f5f5f5',
                       borderwidth=0,
                       arrowsize=12)
        style.configure('Horizontal.TScrollbar',
                       background='#e0e0e0',
                       troughcolor='#f5f5f5',
                       borderwidth=0,
                       arrowsize=12)
        
class EmailClient:
    def __init__(self):
        self.imap_server = "imap.qq.com"
        self.smtp_server = "smtp.qq.com"
        self.email_address = "joryating@qq.com"
        self.password = "xipvhibzgkogdejf"
        self.imap_port = 993
        self.smtp_port = 587
        self.imap_connection = None
        self.smtp_connection = None
        
    def connect_imap(self):
        try:
            self.imap_connection = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            self.imap_connection.login(self.email_address, self.password)
            return True
        except Exception as e:
            print(f"IMAP连接错误: {e}")
            return False
            
    def connect_smtp(self):
        try:
            self.smtp_connection = smtplib.SMTP(self.smtp_server, self.smtp_port)
            self.smtp_connection.starttls()
            self.smtp_connection.login(self.email_address, self.password)
            return True
        except Exception as e:
            print(f"SMTP连接错误: {e}")
            return False
            
    def disconnect(self):
        try:
            if self.imap_connection:
                self.imap_connection.logout()
            if self.smtp_connection:
                self.smtp_connection.quit()
        except:
            pass
            
    def fetch_emails(self, mailbox='INBOX', limit=10):
        if not self.imap_connection:
            if not self.connect_imap():
                return []
                
        try:
            self.imap_connection.select(mailbox)
            status, messages = self.imap_connection.search(None, 'ALL')
            if status != 'OK':
                return []
                
            email_ids = messages[0].split()
            email_ids = email_ids[-limit:] if limit else email_ids
            
            emails = []
            for email_id in reversed(email_ids):
                status, msg_data = self.imap_connection.fetch(email_id, '(RFC822)')
                if status == 'OK':
                    raw_email = msg_data[0][1]
                    email_message = email.message_from_bytes(raw_email)
                    emails.append(self.parse_email(email_message, email_id))
                    
            return emails
        except Exception as e:
            print(f"获取邮件错误: {e}")
            return []
            
    def parse_email(self, email_message, email_id):
        email_data = {
            'id': email_id.decode(),
            'from': email.utils.parseaddr(email_message['From'])[1],
            'to': email.utils.parseaddr(email_message['To'])[1],
            'subject': self.decode_header(email_message['Subject']),
            'date': email.utils.parsedate_to_datetime(email_message['Date']),
            'body': '',
            'attachments': []
        }
        
        # 解析邮件正文和附件
        for part in email_message.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            
            # 跳过多部分容器
            if part.is_multipart():
                continue
                
            # 处理文本部分
            if content_type == "text/plain" and "attachment" not in content_disposition:
                try:
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or 'utf-8'
                    email_data['body'] = payload.decode(charset, errors='replace')
                except Exception as e:
                    print(f"解码邮件正文错误: {e}")
                    email_data['body'] = part.get_payload()
                    
            # 处理附件
            elif "attachment" in content_disposition or part.get_filename():
                try:
                    filename = part.get_filename()
                    if filename:
                        filename = self.decode_header(filename)
                        attachment = {
                            'filename': filename,
                            'content_type': content_type,
                            'payload': part.get_payload(decode=True)
                        }
                        email_data['attachments'].append(attachment)
                except Exception as e:
                    print(f"处理附件错误: {e}")
                    
        return email_data
    
    def decode_header(self, header):
        """解码邮件头信息，处理中文等特殊字符"""
        try:
            if header is None:
                return ""
                
            decoded = []
            for part, charset in email.header.decode_header(header):
                if isinstance(part, bytes):
                    charset = charset or 'utf-8'
                    try:
                        decoded.append(part.decode(charset, errors='replace'))
                    except:
                        decoded.append(part.decode('gbk', errors='replace'))
                else:
                    decoded.append(str(part))
                    
            return ''.join(decoded)
        except Exception as e:
            print(f"解码头信息错误: {e}")
            return str(header)
        
    def send_email(self, to, subject, body, attachments=None):
        if not self.smtp_connection:
            if not self.connect_smtp():
                return False
                
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_address
            msg['To'] = to
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            if attachments:
                for attachment_path in attachments:
                    if os.path.isfile(attachment_path):
                        with open(attachment_path, 'rb') as f:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename="{os.path.basename(attachment_path)}"'
                            )
                            msg.attach(part)
                            
            self.smtp_connection.sendmail(self.email_address, to, msg.as_string())
            return True
        except Exception as e:
            print(f"发送邮件错误: {e}")
            return False
            
    def mark_as_read(self, email_id, mailbox='INBOX'):
        if not self.imap_connection:
            if not self.connect_imap():
                return False
                
        try:
            self.imap_connection.select(mailbox)
            self.imap_connection.store(email_id, '+FLAGS', '\\Seen')
            return True
        except Exception as e:
            print(f"标记已读错误: {e}")
            return False            

class VideoChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ChatAPP")
    
        # 改进的字体设置 - 添加更多备选字体
        font_list = [
            'Microsoft YaHei',  # Windows
            'WenQuanYi Micro Hei',  # Linux
            'PingFang SC',  # Mac
            'SimHei',  # 黑体
            'Arial Unicode MS'  # 跨平台
        ]
        
        # 尝试找到系统可用的中文字体
        available_font = None
        for font in font_list:
            try:
                tk.Label(root, text="测试", font=(font, 10)).destroy()
                available_font = font
                break
            except:
                continue
        
        if available_font is None:
            available_font = 'TkDefaultFont'  # 回退到默认字体
        
        # 设置全局字体
        default_font = (available_font, 10)
        self.root.option_add('*Font', default_font)
        
        # 对于Text控件单独设置字体
        text_font = (available_font, 10)
        
        # 应用扁平化样式
        FlatStyle.configure_styles()
        
        # 设置窗口最小尺寸
        self.root.minsize(1000, 700)
        
        # 网络配置
        self.protocol = "UDP"
        self.ip = "127.0.0.1"
        self.port = 8000
        self.remote_ip = "127.0.0.1"
        self.remote_port = 8001
        
        # 视频参数
        self.cam = cv2.VideoCapture(0)
        self.frame_queue = queue.Queue(maxsize=10)
        self.remote_frame = None
        
        # 消息队列
        self.message_queue = queue.Queue()
        self.received_messages = queue.Queue()
        
        # 网络组件
        self.socket = None
        self.udp_socket = None
        self.connection = None
        self.running = False
        
        # 邮件客户端
        self.email_client = EmailClient()
        self.current_email = None
        self.email_attachments = []
        
        self.create_gui()
        
    def create_gui(self):
        # 主框架
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 视频和邮件框架
        video_frame = ttk.Frame(self.main_frame)
        video_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        email_frame = ttk.Frame(self.main_frame)
        email_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 视频显示区域
        self.local_video = ttk.Label(video_frame)
        self.local_video.grid(row=0, column=0, padx=5, pady=5)
        
        self.remote_video = ttk.Label(video_frame)
        self.remote_video.grid(row=0, column=1, padx=5, pady=5)
        
        # 控制面板
        control_frame = ttk.Frame(video_frame)
        control_frame.grid(row=1, column=0, columnspan=2)
        
        # 网络配置
        ttk.Label(control_frame, text="本地IP:").grid(row=0, column=0)
        self.ip_entry = ttk.Entry(control_frame)
        self.ip_entry.insert(0, self.ip)
        self.ip_entry.grid(row=0, column=1)
        
        ttk.Label(control_frame, text="目标IP:").grid(row=0, column=2)
        self.remote_ip_entry = ttk.Entry(control_frame)
        self.remote_ip_entry.insert(0, self.remote_ip)
        self.remote_ip_entry.grid(row=0, column=3)
        
        ttk.Label(control_frame, text="协议:").grid(row=0, column=4)
        self.protocol_combo = ttk.Combobox(control_frame, values=["TCP", "UDP"])
        self.protocol_combo.current(1)
        self.protocol_combo.grid(row=0, column=5)
        
        # 连接按钮
        self.connect_btn = ttk.Button(control_frame, text="连接", command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=6, padx=5)
        
        # 聊天组件
        self.chat_log = tk.Text(video_frame, height=10, width=60, state='normal')
        self.chat_log.grid(row=2, column=0, columnspan=2, padx=5, pady=5)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(video_frame, command=self.chat_log.yview)
        scrollbar.grid(row=2, column=2, sticky='ns')
        self.chat_log['yscrollcommand'] = scrollbar.set
        
        # 消息输入框和发送按钮
        message_frame = ttk.Frame(video_frame)
        message_frame.grid(row=3, column=0, columnspan=2, sticky='ew', padx=5, pady=5)
        
        self.message_entry = ttk.Entry(message_frame, width=50)
        self.message_entry.pack(side='left', fill='x', expand=True)
        self.message_entry.bind("<Return>", self.send_message)
        
        send_btn = ttk.Button(message_frame, text="发送", command=self.send_message)
        send_btn.pack(side='left', padx=5)
        
        # 邮件配置框架
        email_config_frame = ttk.LabelFrame(email_frame, text="邮件服务器配置")
        email_config_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(email_config_frame, text="IMAP服务器:").grid(row=0, column=0, sticky=tk.W)
        self.imap_server_entry = ttk.Entry(email_config_frame)
        self.imap_server_entry.insert(0, self.email_client.imap_server)
        self.imap_server_entry.grid(row=0, column=1, sticky=tk.EW)
        
        ttk.Label(email_config_frame, text="SMTP服务器:").grid(row=1, column=0, sticky=tk.W)
        self.smtp_server_entry = ttk.Entry(email_config_frame)
        self.smtp_server_entry.insert(0, self.email_client.smtp_server)
        self.smtp_server_entry.grid(row=1, column=1, sticky=tk.EW)
        
        ttk.Label(email_config_frame, text="邮箱地址:").grid(row=2, column=0, sticky=tk.W)
        self.email_entry = ttk.Entry(email_config_frame)
        self.email_entry.insert(0, self.email_client.email_address)
        self.email_entry.grid(row=2, column=1, sticky=tk.EW)
        
        ttk.Label(email_config_frame, text="密码:").grid(row=3, column=0, sticky=tk.W)
        self.password_entry = ttk.Entry(email_config_frame, show="*")
        self.password_entry.insert(0, self.email_client.password)
        self.password_entry.grid(row=3, column=1, sticky=tk.EW)
        
        connect_btn = ttk.Button(email_config_frame, text="连接邮件服务器", command=self.connect_email)
        connect_btn.grid(row=4, column=0, columnspan=2, pady=5)
        
        # 邮件列表框架
        email_list_frame = ttk.LabelFrame(email_frame, text="收件箱")
        email_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.email_tree = ttk.Treeview(email_list_frame, columns=('from', 'subject', 'date'), show='headings')
        self.email_tree.heading('from', text='发件人')
        self.email_tree.heading('subject', text='主题')
        self.email_tree.heading('date', text='日期')
        self.email_tree.column('from', width=150)
        self.email_tree.column('subject', width=200)
        self.email_tree.column('date', width=120)
        
        scrollbar = ttk.Scrollbar(email_list_frame, orient=tk.VERTICAL, command=self.email_tree.yview)
        self.email_tree.configure(yscrollcommand=scrollbar.set)
        
        self.email_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.email_tree.bind('<<TreeviewSelect>>', self.on_email_select)
        
        refresh_btn = ttk.Button(email_list_frame, text="刷新", command=self.refresh_emails)
        refresh_btn.pack(side=tk.BOTTOM, pady=5)
        
        # 邮件内容框架
        email_content_frame = ttk.LabelFrame(email_frame, text="邮件内容")
        email_content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.from_label = ttk.Label(email_content_frame, text="发件人:")
        self.from_label.pack(anchor=tk.W)
        
        self.subject_label = ttk.Label(email_content_frame, text="主题:")
        self.subject_label.pack(anchor=tk.W)
        
        self.date_label = ttk.Label(email_content_frame, text="日期:")
        self.date_label.pack(anchor=tk.W)
        
        self.body_text = tk.Text(email_content_frame, height=10, wrap=tk.WORD)
        self.body_text.pack(fill=tk.BOTH, expand=True)
        
        self.attachment_label = ttk.Label(email_content_frame, text="附件:")
        self.attachment_label.pack(anchor=tk.W)
        
        self.attachment_list = tk.Listbox(email_content_frame, height=3)
        self.attachment_list.pack(fill=tk.BOTH, expand=True)
        
        # 发送邮件框架
        send_email_frame = ttk.LabelFrame(email_frame, text="发送邮件")
        send_email_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(send_email_frame, text="收件人:").grid(row=0, column=0, sticky=tk.W)
        self.to_entry = ttk.Entry(send_email_frame)
        self.to_entry.grid(row=0, column=1, sticky=tk.EW)
        
        ttk.Label(send_email_frame, text="主题:").grid(row=1, column=0, sticky=tk.W)
        self.subject_entry = ttk.Entry(send_email_frame)
        self.subject_entry.grid(row=1, column=1, sticky=tk.EW)
        
        self.message_text = tk.Text(send_email_frame, height=5)
        self.message_text.grid(row=2, column=0, columnspan=2, sticky=tk.EW)
        
        self.attachment_list_send = tk.Listbox(send_email_frame, height=2)
        self.attachment_list_send.grid(row=3, column=0, columnspan=2, sticky=tk.EW)
        
        button_frame = ttk.Frame(send_email_frame)
        button_frame.grid(row=4, column=0, columnspan=2)
        
        add_attachment_btn = ttk.Button(button_frame, text="添加附件", command=self.add_attachment)
        add_attachment_btn.pack(side=tk.LEFT, padx=5)
        
        remove_attachment_btn = ttk.Button(button_frame, text="移除附件", command=self.remove_attachment)
        remove_attachment_btn.pack(side=tk.LEFT, padx=5)
        
        send_email_btn = ttk.Button(button_frame, text="发送邮件", command=self.send_email)
        send_email_btn.pack(side=tk.LEFT, padx=5)
        
        # 视频捕获线程
        self.video_thread = threading.Thread(target=self.capture_video, daemon=True)
        self.video_thread.start()
        
        # 消息处理线程
        self.message_thread = threading.Thread(target=self.process_messages, daemon=True)
        self.message_thread.start()
        
        # 更新视频显示
        self.update_video()
        
    def connect_email(self):
        self.email_client.imap_server = self.imap_server_entry.get()
        self.email_client.smtp_server = self.smtp_server_entry.get()
        self.email_client.email_address = self.email_entry.get()
        self.email_client.password = self.password_entry.get()
        
        if self.email_client.connect_imap() and self.email_client.connect_smtp():
            messagebox.showinfo("成功", "邮件服务器连接成功")
            self.refresh_emails()
        else:
            messagebox.showerror("错误", "无法连接到邮件服务器")
            
    def refresh_emails(self):
        emails = self.email_client.fetch_emails()
        self.email_tree.delete(*self.email_tree.get_children())
        
        for email_data in emails:
            self.email_tree.insert('', 'end', values=(
                email_data['from'],
                email_data['subject'],
                email_data['date'].strftime('%Y-%m-%d %H:%M')
            ), iid=email_data['id'])
            
    def on_email_select(self, event):
        selected_item = self.email_tree.selection()
        if not selected_item:
            return
            
        email_id = selected_item[0]
        emails = self.email_client.fetch_emails()
        
        for email_data in emails:
            if email_data['id'] == email_id:
                self.current_email = email_data
                self.from_label.config(text=f"发件人: {email_data['from']}")
                self.subject_label.config(text=f"主题: {email_data['subject']}")
                self.date_label.config(text=f"日期: {email_data['date'].strftime('%Y-%m-%d %H:%M:%S')}")
                
                self.body_text.config(state=tk.NORMAL)
                self.body_text.delete(1.0, tk.END)
                
                # 设置字体以支持中文显示
                self.body_text.config(font=('Microsoft YaHei', 10))
                self.body_text.insert(tk.END, email_data['body'])
                self.body_text.config(state=tk.DISABLED)
                
                self.attachment_list.delete(0, tk.END)
                for attachment in email_data['attachments']:
                    self.attachment_list.insert(tk.END, attachment['filename'])
                break
                
    def add_attachment(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.email_attachments.append(file_path)
            self.attachment_list_send.delete(0, tk.END)
            for attachment in self.email_attachments:
                self.attachment_list_send.insert(tk.END, os.path.basename(attachment))
                
    def remove_attachment(self):
        selected = self.attachment_list_send.curselection()
        if selected:
            index = selected[0]
            self.email_attachments.pop(index)
            self.attachment_list_send.delete(0, tk.END)
            for attachment in self.email_attachments:
                self.attachment_list_send.insert(tk.END, os.path.basename(attachment))
                
    def send_email(self):
        to = self.to_entry.get()
        subject = self.subject_entry.get()
        body = self.message_text.get(1.0, tk.END)
        
        if not to or not subject:
            messagebox.showerror("错误", "收件人和主题不能为空")
            return
            
        if self.email_client.send_email(to, subject, body, self.email_attachments):
            messagebox.showinfo("成功", "邮件发送成功")
            self.to_entry.delete(0, tk.END)
            self.subject_entry.delete(0, tk.END)
            self.message_text.delete(1.0, tk.END)
            self.attachment_list_send.delete(0, tk.END)
            self.email_attachments = []
        else:
            messagebox.showerror("错误", "邮件发送失败")
            
    # 以下是原有的视频聊天功能方法，保持不变
    def toggle_connection(self):
        if not self.running:
            self.start_connection()
        else:
            self.stop_connection()
            
    def start_connection(self):
        self.protocol = self.protocol_combo.get()
        self.ip = self.ip_entry.get()
        self.remote_ip = self.remote_ip_entry.get()
        
        try:
            if self.protocol == "TCP":
                self.setup_tcp()
            else:
                self.setup_udp()
                
            self.running = True
            self.connect_btn.config(text="断开连接")
            threading.Thread(target=self.receive_data, daemon=True).start()
            threading.Thread(target=self.send_video, daemon=True).start()
            threading.Thread(target=self.send_messages, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("连接错误", str(e))
            
    def setup_tcp(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.bind((self.ip, self.port))
        except Exception as e:
            messagebox.showerror("绑定错误", str(e))
            return
        self.socket.listen(1)
        
        def wait_for_connection():
            try:
                self.connection, _ = self.socket.accept()
                self.root.after(0, lambda: self.connect_btn.config(text="断开连接"))
                self.running = True
                threading.Thread(target=self.receive_data, daemon=True).start()
                threading.Thread(target=self.send_video, daemon=True).start()
                threading.Thread(target=self.send_messages, daemon=True).start()
            except Exception as e:
                print("接受连接错误:", e)
        threading.Thread(target=wait_for_connection, daemon=True).start()
        
    def setup_udp(self):
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind((self.ip, self.port))
        
    def stop_connection(self):
        self.running = False
        if self.socket:
            self.socket.close()
        if self.udp_socket:
            self.udp_socket.close()
        self.connect_btn.config(text="连接")
        
    def capture_video(self):
        while True:
            ret, frame = self.cam.read()
            if ret:
                if self.frame_queue.full():
                    self.frame_queue.get()
                self.frame_queue.put(frame)
                
    def send_video(self):
        while self.running:
            try:
                frame = self.frame_queue.get(timeout=1)
                _, data = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                serialized_data = pickle.dumps(data)
                
                if self.protocol == "TCP":
                    if self.connection:
                        header = struct.pack("L", len(serialized_data))
                        self.connection.sendall(header + serialized_data)
                else:
                    self.udp_socket.sendto(serialized_data, (self.remote_ip, self.remote_port))
            except queue.Empty:
                pass
            except Exception as e:
                print("发送视频错误:", e)
                break
                
    def send_message(self, event=None):
        message = self.message_entry.get().strip()
        if message:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.chat_log.config(state='normal')
            self.chat_log.insert(tk.END, f"[{timestamp}] 我: {message}\n")
            self.chat_log.config(state='disabled')
            self.chat_log.see(tk.END)
            
            # 将消息放入队列等待发送
            message_data = {
                'type': 'message',
                'content': message,
                'timestamp': timestamp
            }
            self.message_queue.put(message_data)
            
            self.message_entry.delete(0, tk.END)
            
    def send_messages(self):
        while self.running:
            try:
                message_data = self.message_queue.get(timeout=1)
                serialized_data = json.dumps(message_data).encode('utf-8')
                
                if self.protocol == "TCP":
                    if self.connection:
                        header = struct.pack("L", len(serialized_data))
                        self.connection.sendall(header + serialized_data)
                else:
                    self.udp_socket.sendto(serialized_data, (self.remote_ip, self.remote_port))
            except queue.Empty:
                pass
            except Exception as e:
                print("发送消息错误:", e)
                break
                
    def process_messages(self):
        while True:
            try:
                message_data = self.received_messages.get(timeout=1)
                self.root.after(0, self.display_message, message_data)
            except queue.Empty:
                pass
                
    def display_message(self, message_data):
        self.chat_log.config(state='normal')
        self.chat_log.insert(tk.END, f"[{message_data['timestamp']}] 对方: {message_data['content']}\n")
        self.chat_log.config(state='disabled')
        self.chat_log.see(tk.END)
                
    def receive_data(self):
        while self.running:
            try:
                if self.protocol == "TCP":
                    if not self.connection:
                        continue
                        
                    # 检查是否有数据可读
                    ready = select.select([self.connection], [], [], 1)
                    if not ready[0]:
                        continue
                        
                    # 读取长度头
                    header = b''
                    while len(header) < 4 and self.running:
                        chunk = self.connection.recv(4 - len(header))
                        if not chunk:
                            break
                        header += chunk
                    if len(header) !=4:
                        break
                        
                    data_len = struct.unpack("L", header)[0]
                    
                    # 读取数据
                    data = b''
                    while len(data) < data_len and self.running:
                        chunk = self.connection.recv(min(4096, data_len - len(data)))
                        if not chunk:
                            break
                        data += chunk
                        
                    if len(data) != data_len:
                        break
                        
                    # 判断数据类型
                    try:
                        # 尝试解码为消息
                        message_data = json.loads(data.decode('utf-8'))
                        if message_data.get('type') == 'message':
                            self.received_messages.put(message_data)
                            continue
                    except:
                        pass
                        
                    # 如果不是消息，则认为是视频帧
                    frame_data = pickle.loads(data)
                    frame = cv2.imdecode(frame_data, cv2.IMREAD_COLOR)
                    if frame is not None:
                        self.remote_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        
                else:  # UDP协议
                    data, _ = self.udp_socket.recvfrom(65536)
                    
                    # 尝试解码为消息
                    try:
                        message_data = json.loads(data.decode('utf-8'))
                        if message_data.get('type') == 'message':
                            self.received_messages.put(message_data)
                            continue
                    except:
                        pass
                        
                    # 如果不是消息，则认为是视频帧
                    frame_data = pickle.loads(data)
                    frame = cv2.imdecode(frame_data, cv2.IMREAD_COLOR)
                    if frame is not None:
                        self.remote_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        
            except Exception as e:
                print("接收错误:", e)
                break
                
    def update_video(self):
        # 更新本地视频
        if not self.frame_queue.empty():
            frame = self.frame_queue.queue[-1]
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = cv2.resize(img, (320, 240))
            img_tk = self.get_tk_image(img)
            self.local_video.config(image=img_tk)
            self.local_video.image = img_tk
            
        # 更新远程视频
        if self.remote_frame is not None:
            img = cv2.resize(self.remote_frame, (320, 240))
            img_tk = self.get_tk_image(img)
            self.remote_video.config(image=img_tk)
            self.remote_video.image = img_tk
            
        self.root.after(50, self.update_video)
        
    def update_video(self):
        # 更新本地视频
        if not self.frame_queue.empty():
            frame = self.frame_queue.queue[-1]
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = cv2.resize(img, (320, 240))
            img_tk = self.get_tk_image(img)
            self.local_video.config(image=img_tk)
            self.local_video.image = img_tk
            
        # 更新远程视频
        if self.remote_frame is not None:
            img = cv2.resize(self.remote_frame, (320, 240))
            img_tk = self.get_tk_image(img)
            self.remote_video.config(image=img_tk)
            self.remote_video.image = img_tk
            
        self.root.after(50, self.update_video)
        
    def get_tk_image(self, image):
        from PIL import Image, ImageTk
        return ImageTk.PhotoImage(image=Image.fromarray(image))        

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoChatApp(root)
    root.mainloop()
