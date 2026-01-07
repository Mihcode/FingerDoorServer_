from sqlalchemy import create_engine # engine để kế nối tới db
from sqlalchemy.ext.declarative import declarative_base # để tạo base class cho các model ORM
from sqlalchemy.orm import sessionmaker # để tạo session tương tác với db
import os # để làm việc với biến môi trường
from dotenv import load_dotenv # để tải biến môi trường từ file .env

load_dotenv() # tải biến môi trường từ file .env
DATABASE_URL = os.getenv("DATABASE_URL")
# Lấy URL kết nối tới database từ biến môi trường

engine = create_engine(DATABASE_URL) # tạo đối tượng engine giao tiếp db // không trực tiếp query 
# Tạo facetory SessionLocal để nó sinh ra các session làm việc với DB
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) #chỉ định dùng engine vừa tạo và thiết lập commit thủ công và tắt tự động flush

Base = declarative_base() # tạo base class cho các model ORM, khi định nghĩa orm model sẽ kế thừa từ đây

# lấy DB session
def get_db():
    db = SessionLocal() # tạo session mới
    try
        yield db # yield để trả về session và giữ kết nối mở
    finally:
        db.close() # đóng session sau khi sử dụng xong