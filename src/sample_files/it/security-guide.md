# Hướng dẫn Bảo mật

## Classification: SECRET
**Department: IT Only | Clearance: Secret+**

## Chính sách mật khẩu
- Độ dài tối thiểu: 12 ký tự
- Phải bao gồm: chữ hoa, chữ thường, số, ký tự đặc biệt
- Thay đổi mỗi 90 ngày

## Firewall Rules
```
# Production
ALLOW TCP 443 FROM 0.0.0.0/0
DENY ALL FROM 0.0.0.0/0
```

## Incident Response
1. Phát hiện → Báo cáo IT Security
2. Cô lập hệ thống bị ảnh hưởng
3. Phân tích và khắc phục
4. Báo cáo post-incident

## Liên hệ khẩn cấp
- Security Team: security@company.com
- CSIRT Hotline: 1800-XXXX

---
*Tài liệu SECRET - Chỉ dành cho IT có clearance phù hợp*
