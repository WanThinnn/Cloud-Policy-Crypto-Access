# OpenVPN PQC Native

Cấu trúc thư mục này chứa file cài đặt OpenVPN 3.5 hỗ trợ native Post-Quantum Cryptography (ML-DSA-87) thông qua OpenSSL.

## Tính năng
- **Base image:** `ubuntu:26.04` (Chứa sẵn OpenVPN 3.5 & OpenSSL 3.5)
- **Thuật toán chữ ký:** `ML-DSA-87` cho toàn bộ chứng chỉ Root CA, Server và Client.
- **TLS 1.3:** Ép buộc TLS 1.3 để sử dụng Hybrid KEM (X25519MLKEM768).
- **NAT:** Tự động định tuyến (masquerade) traffic từ VPN vào mạng nội bộ của Docker (`app-network`).

## Cách sử dụng

OpenVPN server đã được tích hợp sẵn vào `docker-compose.yml` (và `docker-compose.prod.yml`) dưới một profile riêng tên là `vpn`.

### 1. Khởi động cùng với hệ thống
Để bật VPN cùng lúc với Web và Vault, bạn hãy thêm tham số `--profile vpn` khi chạy lệnh docker compose:

```bash
docker compose -f docker/docker-compose.yml --profile vpn up -d
```
*(Nếu bạn dùng `start.py`, bạn có thể sửa lệnh gọi docker compose bên trong file `start.py` hoặc chạy thủ công lệnh trên).*

Lần đầu tiên chạy, container `openvpn_server` sẽ tự động:
- Khởi tạo PKI bằng OpenSSL.
- Tạo Root CA (ML-DSA-87).
- Tạo Server Certificate (ML-DSA-87).
- Tạo TLS-Crypt-V2 key.

Tất cả dữ liệu được lưu trong Docker Volume `openvpn_data`.

### 2. Tạo Client Profile (.ovpn) cho người dùng
Để tạo file `.ovpn` cho máy khách (ví dụ tên `my_laptop`), hãy chạy lệnh sau từ máy chủ (trên cửa sổ CMD/Bash):

```bash
# 1. Tạo Client Certificate bên trong container
docker exec -it openvpn_server bash -c "cd /etc/openvpn/pki && openssl req -new -newkey mldsa87 -keyout private/my_laptop.key -out my_laptop.csr -nodes -subj '/C=VN/O=CyberFortress/OU=CyberFortress VPN/CN=my_laptop' && openssl x509 -req -in my_laptop.csr -CA ca.crt -CAkey private/ca.key -CAcreateserial -out issued/my_laptop.crt -days 3650"

# 2. Sinh ra file my_laptop.ovpn
# Lệnh dưới đây gom ca.crt, tls-crypt-v2, client cert và key vào 1 file duy nhất.
docker exec -it openvpn_server bash -c "cat /etc/openvpn/server.conf.template | sed 's/cyberfortress-vpn-server.crt/my_laptop.crt/' | sed 's/cyberfortress-vpn-server.key/my_laptop.key/' > /tmp/my_laptop.ovpn && echo '<ca>' >> /tmp/my_laptop.ovpn && cat /etc/openvpn/pki/ca.crt >> /tmp/my_laptop.ovpn && echo '</ca><cert>' >> /tmp/my_laptop.ovpn && cat /etc/openvpn/pki/issued/my_laptop.crt >> /tmp/my_laptop.ovpn && echo '</cert><key>' >> /tmp/my_laptop.ovpn && cat /etc/openvpn/pki/private/my_laptop.key >> /tmp/my_laptop.ovpn && echo '</key><tls-crypt-v2>' >> /tmp/my_laptop.ovpn && cat /etc/openvpn/tls-crypt-v2-server.key >> /tmp/my_laptop.ovpn && echo '</tls-crypt-v2>'"

# 3. Copy file .ovpn ra ngoài máy chủ
docker cp openvpn_server:/tmp/my_laptop.ovpn ./my_laptop.ovpn
docker cp openvpn_server:/etc/openvpn/CyberFortress-VPN-RootCA.crt .
```

File `my_laptop.ovpn` vừa được tạo ra chính là file kết nối mang bảo mật lượng tử toàn diện. Hãy đưa file này vào OpenVPN Connect trên máy khách (yêu cầu bản mới hỗ trợ OpenVPN 3.5).

### Lời kết
Chúc mừng bạn đã sở hữu một hạ tầng VPN **Native PQC** siêu bảo mật!
