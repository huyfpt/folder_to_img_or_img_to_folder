import os
import zipfile
import numpy as np
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from PIL import Image
import io
import re

# Tăng giới hạn Pillow để tránh lỗi "Decompression Bomb"
Image.MAX_IMAGE_PIXELS = None

# Hàm tạo khóa từ mật khẩu nhập vào
def get_key_from_password():
    password = input("\U0001F511 Nhập mật khẩu: ").strip().encode()
    if len(password) < 16:
        password = password.ljust(16, b'\x00')
    elif 16 < len(password) < 24:
        password = password.ljust(24, b'\x00')
    elif 24 < len(password) < 32:
        password = password.ljust(32, b'\x00')
    elif len(password) > 32:
        password = password[:32]  # Cắt bớt nếu quá dài
    return password

SECRET_KEY = get_key_from_password()

def decode_images(image_paths):
    full_data = b""
    for img_path in image_paths:
        try:
            img = Image.open(img_path)
            data = np.array(img).flatten().tobytes().rstrip(b"\x00")
            full_data += data
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

def main():
    choice = input("1️⃣  Mã hóa thư mục thành ảnh\n2️⃣  Giải mã ảnh thành thư mục\n3️⃣  Giải mã từ danh sách ảnh\nNhập lựa chọn (1/2/3): ")
    
    if choice == "2":
        image_folder = input("\U0001F4C1 Nhập thư mục chứa ảnh mã hóa: ").strip()
        if not os.path.exists(image_folder):
            print("\u274C Thư mục không tồn tại!")
            return
        
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
            encrypted_data = decode_images(note_files)
            decrypted_data = decrypt_data(encrypted_data, SECRET_KEY)
            if decrypted_data:
                unzip_file(decrypted_data, "output_folder")
        
        # Giải mã từng file riêng lẻ
        for img in other_files:
            print(f"\U0001F4A1 Đang giải mã file đơn '{img}'...")
            encrypted_data = decode_images([img])
            decrypted_data = decrypt_data(encrypted_data, SECRET_KEY)
            if decrypted_data:
                unzip_file(decrypted_data, f"output_{os.path.splitext(os.path.basename(img))[0]}")
        
        print("✅ Giải mã hoàn tất!")
    
    elif choice == "3":
        image_files = input("\U0001F5BC Nhập danh sách ảnh mã hóa (cách nhau bởi dấu phẩy): ").split(",")
        image_files = [img.strip() for img in image_files if img.strip().endswith(".png")]
        if not image_files:
            print("\u274C Không có file hợp lệ!")
            return
        
        encrypted_data = decode_images(image_files)
        decrypted_data = decrypt_data(encrypted_data, SECRET_KEY)
        
        if decrypted_data:
            unzip_file(decrypted_data, "output_folder")
        
        print("✅ Giải mã hoàn tất!")
    
    else:
        print("❌ Lựa chọn không hợp lệ!")

if __name__ == "__main__":
    main()
