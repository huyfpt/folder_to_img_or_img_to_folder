import os
import zipfile
import numpy as np
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from PIL import Image
import io
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading

# Tăng giới hạn Pillow để tránh lỗi "Decompression Bomb"
Image.MAX_IMAGE_PIXELS = None

# Hàm tạo khóa từ mật khẩu nhập vào
def get_key_from_password(password):
    password = password.strip().encode()
    if len(password) < 16:
        password = password.ljust(16, b'\x00')
    elif 16 < len(password) < 24:
        password = password.ljust(24, b'\x00')
    elif 24 < len(password) < 32:
        password = password.ljust(32, b'\x00')
    elif len(password) > 32:
        password = password[:32]  # Cắt bớt nếu quá dài
    return password

def decode_images(image_paths, progress_callback):
    full_data = b""
    total_files = len(image_paths)
    for idx, img_path in enumerate(image_paths):
        try:
            img = Image.open(img_path)
            data = np.array(img).flatten().tobytes().rstrip(b"\x00")
            full_data += data
            progress_callback(idx + 1, total_files)
            print(f"\u2705 Đã trích xuất dữ liệu từ '{img_path}' ({len(data)} bytes)")
        except Exception as e:
            print(f"\u274C Lỗi đọc ảnh '{img_path}': {e}")
    return full_data

# Giải mã dữ liệu
def decrypt_data(encrypted_data, key):
    if len(encrypted_data) % 16 != 0:
        print("\u274C Dữ liệu bị lỗi, không phải bội số của 16!")
        return None
    iv, encrypted_data = encrypted_data[:AES.block_size], encrypted_data[AES.block_size:]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(encrypted_data), AES.block_size)

# Giải nén file ZIP
def unzip_file(zip_data, output_folder):
    try:
        with zipfile.ZipFile(io.BytesIO(zip_data), "r") as zipf:
            zipf.extractall(output_folder)
        print(f"\u2705 Đã giải nén vào '{output_folder}'")
    except zipfile.BadZipFile:
        print("\u274C File ZIP không hợp lệ!")

# Giải mã thư mục ảnh
def process_decrypt_folder(image_folder, password, progress_callback, finish_callback):
    SECRET_KEY = get_key_from_password(password)
    
    image_files = [os.path.join(image_folder, f) for f in sorted(os.listdir(image_folder)) if f.lower().endswith(".png")]
    if not image_files:
        print("\u274C Không tìm thấy ảnh mã hóa trong thư mục!")
        return
    
    # Phân loại file
    note_files = sorted([f for f in image_files if re.match(r".*note(\d+)\.png", os.path.basename(f))], key=lambda x: int(re.search(r"\d+", x).group()))
    other_files = [f for f in image_files if f not in note_files]
    
    # Giải mã tập hợp note{number}.png
    if note_files:
        print("\U0001F4A1 Đang giải mã tập hợp note{number}.png...")
        encrypted_data = decode_images(note_files, progress_callback)
        decrypted_data = decrypt_data(encrypted_data, SECRET_KEY)
        if decrypted_data:
            unzip_file(decrypted_data, "output_folder")
    
    # Giải mã từng file riêng lẻ
    for img in other_files:
        print(f"\U0001F4A1 Đang giải mã file đơn '{img}'...")
        encrypted_data = decode_images([img], progress_callback)
        decrypted_data = decrypt_data(encrypted_data, SECRET_KEY)
        if decrypted_data:
            unzip_file(decrypted_data, f"output_{os.path.splitext(os.path.basename(img))[0]}")
    
    print("✅ Giải mã hoàn tất!")
    finish_callback()

# Mã hóa thư mục thành ảnh
def process_encrypt_folder(folder, password, progress_callback, finish_callback):
    SECRET_KEY = get_key_from_password(password)

    # Tạo thư mục lưu ảnh mã hóa
    output_folder = os.path.join(folder, "encrypted_images_output")
    os.makedirs(output_folder, exist_ok=True)

    # Nén thư mục thành file ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(folder):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, folder)
                zipf.write(file_path, arcname)

    # Mã hóa dữ liệu
    encrypted_data = zip_buffer.getvalue()
    cipher = AES.new(SECRET_KEY, AES.MODE_CBC)
    iv = cipher.iv
    encrypted_data = iv + cipher.encrypt(pad(encrypted_data, AES.block_size))

    # Chia dữ liệu thành nhiều ảnh (mỗi ảnh 50MB)
    chunk_size = 50 * 1024 * 1024  # 50MB
    img_width = 5000  # Chiều rộng cố định (có thể thay đổi)
    
    total_chunks = (len(encrypted_data) + chunk_size - 1) // chunk_size  # Tổng số ảnh cần tạo

    for idx, chunk_start in enumerate(range(0, len(encrypted_data), chunk_size)):
        chunk = encrypted_data[chunk_start:chunk_start + chunk_size]

        # Tính toán chiều cao dựa trên kích thước dữ liệu
        height = (len(chunk) + img_width - 1) // img_width

        # Tạo ma trận ảnh
        padded_chunk = chunk.ljust(img_width * height, b'\x00')  # Đệm dữ liệu để đủ shape
        img_array = np.frombuffer(padded_chunk, dtype=np.uint8).reshape((height, img_width))

        # Lưu ảnh
        img = Image.fromarray(img_array)
        img_path = os.path.join(output_folder, f"note{idx+1}.png")
        img.save(img_path)

        # 🔹 Cập nhật progress bar
        progress_callback(idx + 1, total_chunks)

    print(f"✅ Mã hóa thư mục hoàn tất! Ảnh được lưu tại: {output_folder}")
    finish_callback()

# Giải mã từ danh sách ảnh
def process_decrypt_images(image_files, password, progress_callback, finish_callback):
    SECRET_KEY = get_key_from_password(password)
    
    total_files = len(image_files)
    full_data = b""

    for idx, img_path in enumerate(image_files):
        try:
            img = Image.open(img_path)
            data = np.array(img).flatten().tobytes().rstrip(b"\x00")
            full_data += data

            # 🔹 Cập nhật progress bar
            progress_callback(idx + 1, total_files)

        except Exception as e:
            print(f"\u274C Lỗi đọc ảnh '{img_path}': {e}")

    decrypted_data = decrypt_data(full_data, SECRET_KEY)
    if decrypted_data:
        unzip_file(decrypted_data, "output_folder")

    print("✅ Giải mã hoàn tất!")
    finish_callback()


# Tạo giao diện Tkinter
def open_main_ui():
    def on_process():
        password = password_entry.get()
        if not password:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập mật khẩu!")
            return
        choice = choice_var.get()
        if choice == "1":
            folder = filedialog.askdirectory(title="Chọn thư mục cần mã hóa")
            if folder:
                progress_bar["value"] = 0
                threading.Thread(target=process_encrypt_folder, args=(folder, password, update_progress, show_finish_message)).start()
        elif choice == "2":
            image_folder = filedialog.askdirectory(title="Chọn thư mục chứa ảnh mã hóa")
            if image_folder:
                progress_bar["value"] = 0
                threading.Thread(target=process_decrypt_folder, args=(image_folder, password, update_progress, show_finish_message)).start()
        elif choice == "3":
            image_files = filedialog.askopenfilenames(title="Chọn các ảnh cần giải mã", filetypes=[("PNG files", "*.png")])
            if image_files:
                progress_bar["value"] = 0
                threading.Thread(target=process_decrypt_images, args=(image_files, password, update_progress, show_finish_message)).start()

    def update_progress(current, total):
        progress_bar["maximum"] = total
        progress_bar["value"] = current
        root.update_idletasks()  # Cập nhật UI ngay lập tức

    def show_finish_message():
        messagebox.showinfo("Hoàn tất", "✅ Quá trình đã hoàn tất!")
        reset_ui()

    def reset_ui():
        progress_bar["value"] = 0
        select_button.config(state="normal")

    root = tk.Tk()
    root.title("Chọn tác vụ")

    # Nhập mật khẩu
    password_label = tk.Label(root, text="Mật khẩu:")
    password_label.pack(pady=5)
    password_entry = tk.Entry(root, show="*")
    password_entry.pack(pady=5)

    # Chọn tác vụ
    choice_label = tk.Label(root, text="Chọn tác vụ:")
    choice_label.pack(pady=5)
    choice_var = tk.StringVar(value="1")
    choice_1 = tk.Radiobutton(root, text="Mã hóa thư mục thành ảnh", variable=choice_var, value="1")
    choice_1.pack(anchor="w")
    choice_2 = tk.Radiobutton(root, text="Giải mã ảnh thành thư mục", variable=choice_var, value="2")
    choice_2.pack(anchor="w")
    choice_3 = tk.Radiobutton(root, text="Giải mã từ danh sách ảnh", variable=choice_var, value="3")
    choice_3.pack(anchor="w")

    # Nút để chọn thư mục ảnh
    select_button = tk.Button(root, text="Bắt đầu", command=on_process)
    select_button.pack(pady=20)

    # Thanh tiến trình
    progress_bar = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
    progress_bar.pack(pady=20)

    # Chạy giao diện Tkinter
    root.mainloop()

if __name__ == "__main__":
    open_main_ui()
