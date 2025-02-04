import os
import zipfile
import numpy as np
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from PIL import Image
import io

# Tăng giới hạn Pillow để tránh lỗi "Decompression Bomb"
Image.MAX_IMAGE_PIXELS = None

# Hàm tạo khóa từ mật khẩu nhập vào
def get_key_from_password():
    password = input("🔑 Nhập mật khẩu: ").strip().encode()
    
    # Đảm bảo độ dài hợp lệ bằng cách cắt hoặc thêm '\x00'
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


# SECRET_KEY = b""  # 16, 24, 32 bytes

# Nén thư mục thành file ZIP
def zip_folder(folder_path, output_zip):
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, start=folder_path)
                zipf.write(file_path, arcname=arcname)
    print(f"✅ Đã nén '{folder_path}' thành '{output_zip}'")

# Mã hóa dữ liệu
def encrypt_data(data, key):
    cipher = AES.new(key, AES.MODE_CBC)
    iv = cipher.iv
    encrypted_data = cipher.encrypt(pad(data, AES.block_size))
    return iv + encrypted_data

# Nhúng dữ liệu vào ảnh, chia nhỏ nếu quá lớn
def encode_image(data, output_prefix, max_size=50 * 1024 * 1024):  # 50MB mỗi ảnh (chia nhỏ nếu quá lớn)
    num_parts = (len(data) // max_size) + 1
    print(f"🖼 Tổng dữ liệu: {len(data)} bytes, Số ảnh cần tạo: {num_parts}")

    for i in range(num_parts):
        part_data = data[i * max_size: (i + 1) * max_size]
        if len(part_data) % 3 != 0:
            part_data += b'\x00' * (3 - len(part_data) % 3)
        
        size = int(np.ceil((len(part_data) // 3) ** 0.5))
        img = np.zeros((size, size, 3), dtype=np.uint8)
        img_data = np.frombuffer(part_data, dtype=np.uint8)
        img_data = np.pad(img_data, (0, size * size * 3 - len(img_data)), 'constant')
        img = img_data.reshape(size, size, 3)
        
        img_filename = f"{output_prefix}{i+1}.png"
        Image.fromarray(img).save(img_filename)
        print(f"✅ Đã lưu ảnh mã hóa '{img_filename}' ({len(part_data)} bytes)")

# Trích xuất dữ liệu từ danh sách ảnh
def decode_images(image_paths):
    full_data = b""
    for img_path in image_paths:
        try:
            img = Image.open(img_path)
            data = np.array(img).flatten().tobytes().rstrip(b"\x00")
            full_data += data
            print(f"✅ Đã trích xuất dữ liệu từ '{img_path}' ({len(data)} bytes)")
        except Exception as e:
            print(f"❌ Lỗi đọc ảnh '{img_path}': {e}")
    return full_data

# Giải mã dữ liệu
def decrypt_data(encrypted_data, key):
    if len(encrypted_data) % 16 != 0:
        print("❌ Dữ liệu bị lỗi, không phải bội số của 16!")
        return None
    
    iv, encrypted_data = encrypted_data[:AES.block_size], encrypted_data[AES.block_size:]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(encrypted_data), AES.block_size)

# Giải nén file ZIP
def unzip_file(zip_data, output_folder):
    try:
        with zipfile.ZipFile(io.BytesIO(zip_data), "r") as zipf:
            zipf.extractall(output_folder)
        print(f"✅ Đã giải nén vào '{output_folder}'")
    except zipfile.BadZipFile:
        print("❌ File ZIP không hợp lệ!")

# Chương trình chính
def main():
    choice = input("1️⃣  Mã hóa thư mục thành ảnh\n2️⃣  Giải mã ảnh thành thư mục\nNhập lựa chọn (1/2): ")
    
    if choice == "1":
        folder_path = input("📂 Nhập thư mục cần mã hóa: ")
        zip_path = "temp.zip"
        output_prefix = "note"
        
        zip_folder(folder_path, zip_path)
        with open(zip_path, "rb") as f:
            zip_data = f.read()
        
        encrypted_data = encrypt_data(zip_data, SECRET_KEY)
        encode_image(encrypted_data, output_prefix)
        os.remove(zip_path)
        print("✅ Mã hóa hoàn tất!")
    
    elif choice == "2":
        image_files = input("📸 Nhập danh sách ảnh mã hóa (cách nhau bởi dấu phẩy): ").split(",")
        image_files = [img.strip() for img in image_files]
        output_folder = "output_folder"
        
        encrypted_data = decode_images(image_files)
        decrypted_data = decrypt_data(encrypted_data, SECRET_KEY)
        
        if decrypted_data:
            unzip_file(decrypted_data, output_folder)
        
        print("✅ Giải mã hoàn tất!")
    else:
        print("❌ Lựa chọn không hợp lệ!")

if __name__ == "__main__":
    main()
