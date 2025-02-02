import os
import zipfile
import numpy as np
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from PIL import Image
import io

# 🔑 Khóa cố định (có thể thay đổi hoặc sinh ngẫu nhiên)
SECRET_KEY = b"ThisIsASecretKey"  # Độ dài 16, 24, 32 bytes

# 📂 **Hàm nén thư mục thành file ZIP**
def zip_folder(folder_path, output_zip):
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, folder_path))
    print(f"✅ Đã nén {folder_path} thành {output_zip}")

# 🔐 **Hàm mã hóa dữ liệu**
def encrypt_data(data, key):
    cipher = AES.new(key, AES.MODE_CBC)  # Tạo AES với chế độ CBC
    iv = cipher.iv  # Lấy IV ngẫu nhiên
    encrypted_data = cipher.encrypt(pad(data, AES.block_size))  # Mã hóa + Padding
    return iv + encrypted_data  # Ghép IV vào dữ liệu

# 🖼 **Hàm nhúng dữ liệu vào ảnh**
def encode_image(data, output_image):
    # Tính toán kích thước ảnh dựa trên độ dài dữ liệu
    size = int(np.ceil(len(data) ** 0.5))  
    img = np.zeros((size, size, 3), dtype=np.uint8)  # Tạo ảnh trống
    
    flat_data = np.frombuffer(data, dtype=np.uint8)  # Chuyển dữ liệu thành mảng byte
    data_size = flat_data.size - (flat_data.size % 3)  # Đảm bảo kích thước là bội số của 3
    
    # Reshape the data and fill the image pixels row by row
    reshaped_data = flat_data[:data_size].reshape(-1, 3)  # Ensure the data is reshaped correctly into RGB triplets
    
    # Ensure that reshaped data fits into the image shape
    for i in range(reshaped_data.shape[0]):
        row = i // size  # Calculate row index
        col = i % size   # Calculate column index
        img[row, col] = reshaped_data[i]  # Set pixel RGB values
    
    # Lưu ảnh
    Image.fromarray(img).save(output_image)
    print(f"✅ Đã lưu ảnh mã hóa tại {output_image}")

# 📤 **Hàm trích xuất dữ liệu từ ảnh**
def decode_image(input_image):
    img = Image.open(input_image)
    data = np.array(img).flatten().tobytes()
    return data.rstrip(b"\x00")  # Loại bỏ byte thừa

# 🔓 **Hàm giải mã dữ liệu**
def decrypt_data(encrypted_data, key):
    iv = encrypted_data[:AES.block_size]  # Lấy IV
    encrypted_data = encrypted_data[AES.block_size:]  # Lấy phần dữ liệu
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(encrypted_data), AES.block_size)  # Giải mã + Unpad

# 📂 **Hàm giải nén ZIP**
def unzip_file(zip_data, output_folder):
    with zipfile.ZipFile(io.BytesIO(zip_data), "r") as zipf:
        zipf.extractall(output_folder)
    print(f"✅ Đã giải nén vào {output_folder}")

# 🚀 **Hàm chính**
def main():
    choice = input("1️⃣  Mã hóa thư mục thành ảnh\n2️⃣  Giải mã ảnh thành thư mục\nNhập lựa chọn (1/2): ")
    
    if choice == "1":
        folder_path = input("📂 Nhập đường dẫn thư mục cần mã hóa: ")
        zip_path = "temp.zip"
        output_image = "output.png"

        zip_folder(folder_path, zip_path)
        
        with open(zip_path, "rb") as f:
            zip_data = f.read()

        encrypted_data = encrypt_data(zip_data, SECRET_KEY)
        encode_image(encrypted_data, output_image)
        
        os.remove(zip_path)  # Xóa file tạm
        print("✅ Mã hóa hoàn tất!")
    
    elif choice == "2":
        input_image = input("📸 Nhập đường dẫn ảnh mã hóa: ")
        output_folder = "output_folder"

        encrypted_data = decode_image(input_image)
        decrypted_data = decrypt_data(encrypted_data, SECRET_KEY)
        unzip_file(decrypted_data, output_folder)
        
        print("✅ Giải mã hoàn tất!")

    else:
        print("❌ Lựa chọn không hợp lệ!")

if __name__ == "__main__":
    main()
