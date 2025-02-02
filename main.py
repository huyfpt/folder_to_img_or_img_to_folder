import os
import zipfile
import numpy as np
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from PIL import Image
import io

# 🔑 Khóa mã hóa cố định (16, 24 hoặc 32 bytes)
SECRET_KEY = b""

# 📂 Hàm nén thư mục thành ZIP
def zip_folder(folder_path, output_zip):
    try:
        with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, start=folder_path)
                    zipf.write(file_path, arcname=arcname)
        print(f"✅ Đã nén thư mục '{folder_path}' thành '{output_zip}'")
        return True
    except Exception as e:
        print(f"❌ Lỗi nén thư mục: {e}")
        return False

# 🔐 Hàm mã hóa dữ liệu
def encrypt_data(data, key):
    cipher = AES.new(key, AES.MODE_CBC)
    iv = cipher.iv
    padded_data = pad(data, AES.block_size)

    encrypted_data = cipher.encrypt(padded_data)
    print(f"🔐 Kích thước dữ liệu gốc: {len(data)} bytes")
    print(f"🔐 Kích thước dữ liệu sau padding: {len(padded_data)} bytes")
    print(f"🔐 Kích thước dữ liệu sau mã hóa: {len(encrypted_data)} bytes (bội số của 16)")

    return iv + encrypted_data
# 🖼 Hàm nhúng dữ liệu vào ảnh
def encode_image(data, output_image):
    original_size = len(data)

    # ✅ Đảm bảo dữ liệu là bội số của 3
    if len(data) % 3 != 0:
        padding_size = 3 - (len(data) % 3)
        data += b'\x00' * padding_size  

    # ✅ Tính toán kích thước ảnh chính xác hơn
    total_pixels = len(data) // 3
    size = int(np.ceil(total_pixels ** 0.5))  # Lấy căn bậc 2, làm tròn lên

    # ✅ Tạo ảnh phù hợp với dữ liệu
    img = np.zeros((size, size, 3), dtype=np.uint8)
    flat_data = np.frombuffer(data, dtype=np.uint8)
    
    # ✅ Resize dữ liệu để khớp kích thước ảnh
    needed_size = size * size * 3
    if len(flat_data) < needed_size:
        flat_data = np.pad(flat_data, (0, needed_size - len(flat_data)), 'constant')

    img_data = flat_data.reshape(size, size, 3)

    Image.fromarray(img_data).save(output_image)
    print(f"✅ Đã lưu ảnh mã hóa tại '{output_image}'")
    print(f"🖼 Kích thước dữ liệu trước khi nhúng: {original_size} bytes")
    print(f"🖼 Kích thước ảnh: {size}x{size} pixels")

# 📤 Hàm trích xuất dữ liệu từ ảnh
def decode_image(input_image):
    try:
        img = Image.open(input_image)
        data = np.array(img).flatten().tobytes()

        print(f"🖼 Kích thước dữ liệu trích xuất: {len(data)} bytes")
        return data.rstrip(b"\x00")  # Loại bỏ padding
    except Exception as e:
        print(f"❌ Lỗi đọc ảnh: {e}")
        return None

# 🔓 Hàm giải mã dữ liệu
def decrypt_data(encrypted_data, key):
    if len(encrypted_data) < AES.block_size:
        print("❌ Dữ liệu không đủ để giải mã!")
        return None

    iv = encrypted_data[:AES.block_size]
    encrypted_data = encrypted_data[AES.block_size:]

    if len(encrypted_data) % AES.block_size != 0:
        print(f"❌ Kích thước dữ liệu lỗi: {len(encrypted_data)} bytes (không phải bội số của 16)")
        return None

    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted_data = cipher.decrypt(encrypted_data)

    try:
        unpadded_data = unpad(decrypted_data, AES.block_size)
        print(f"🔓 Kích thước dữ liệu giải mã: {len(unpadded_data)} bytes")
        return unpadded_data
    except ValueError:
        print("❌ Dữ liệu không hợp lệ sau giải mã! Có thể bị lỗi padding.")
        return None

# 📂 Hàm giải nén ZIP
def unzip_file(zip_data, output_folder):
    try:
        with zipfile.ZipFile(io.BytesIO(zip_data), "r") as zipf:
            zipf.extractall(output_folder)
        print(f"✅ Đã giải nén thành công vào '{output_folder}'")
    except zipfile.BadZipFile:
        print("❌ File ZIP không hợp lệ!")

# 🚀 Hàm chính
def main():
    choice = input("1️⃣  Mã hóa thư mục thành ảnh\n2️⃣  Giải mã ảnh thành thư mục\nNhập lựa chọn (1/2): ")
    
    if choice == "1":
        folder_path = input("📂 Nhập thư mục cần mã hóa: ")
        zip_path = "temp.zip"
        output_image = "output.png"

        if not zip_folder(folder_path, zip_path):
            return

        with open(zip_path, "rb") as f:
            zip_data = f.read()

        encrypted_data = encrypt_data(zip_data, SECRET_KEY)
        encode_image(encrypted_data, output_image)

        os.remove(zip_path)
        print("✅ Mã hóa hoàn tất!")

    elif choice == "2":
        input_image = input("📸 Nhập ảnh mã hóa: ")
        output_folder = "output_folder"

        encrypted_data = decode_image(input_image)
        if encrypted_data is None:
            return

        decrypted_data = decrypt_data(encrypted_data, SECRET_KEY)
        if decrypted_data is None:
            return

        unzip_file(decrypted_data, output_folder)
        print("✅ Giải mã hoàn tất!")

    else:
        print("❌ Lựa chọn không hợp lệ!")

if __name__ == "__main__":
    main()

