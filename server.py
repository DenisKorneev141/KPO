import socket
import json
import os
from datetime import datetime
import sqlite3
import struct

HOST = '127.0.0.1'
PORT = 5555

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen()

print("Сервер запущен, ожидаем подключений...")

def save_json(data, folder="requests", filename_prefix="registration"):
    if not os.path.exists(folder):
        os.makedirs(folder)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.json"
    filepath = os.path.join(folder, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print(f"JSON сохранён: {filepath}")

def get_car_data():
    """Получает данные о машинах из базы данных"""
    conn = sqlite3.connect('cash/carsharing.db')
    cursor = conn.cursor()

    cursor.execute('''SELECT cars.name, cars.model, cars.number, cars.price, cars.status, 
                      locations.address, locations.latitude, locations.longitude, cars.image_path
                      FROM cars
                      JOIN locations ON cars.id = locations.car_id''')

    cars = cursor.fetchall()
    conn.close()
    
    result = []
    for car in cars:
        result.append({
            "name": car[0],
            "model": car[1],
            "number": car[2],
            "price": car[3],
            "status": car[4],
            "address": car[5],
            "latitude": car[6],
            "longitude": car[7],
            "image_path": car[8]
        })
    
    return result

while True:
    conn, addr = server_socket.accept()
    with conn:
        print(f"Подключение от {addr}")

        try:
            # Получаем размер данных (4 байта)
            size_bytes = conn.recv(4)
            if not size_bytes or len(size_bytes) != 4:
                continue
                
            data_size = struct.unpack('!I', size_bytes)[0]
            
            # Получаем JSON-данные
            data = b""
            while len(data) < data_size:
                packet = conn.recv(min(4096, data_size - len(data)))
                if not packet:
                    break
                data += packet

            # Декодируем JSON
            json_data = json.loads(data.decode('utf-8'))
            message_type = json_data.get("type")
            message_data = json_data.get("data")

            print(f"Получен JSON типа '{message_type}': {message_data}")

            if message_type == "registration":
                print("Обрабатываем регистрацию:", message_data)
                save_json(message_data)
                response = {"status": "success"}

            elif message_type == "login":
                login = message_data["login"]
                password = message_data["password"]

                conn_db = sqlite3.connect("cash/carsharing.db")
                cursor = conn_db.cursor()
                cursor.execute("SELECT * FROM users WHERE phone_number = ? AND password = ?", (login, password))
                user = cursor.fetchone()
                conn_db.close()

                if user:
                    print("Проверка удалась")
                    response = {"status": "success", "command": "run_script"}
                else:
                    response = {
                        "status": "error",
                        "message": "Ошибка входа в приложение.\n\n"
                                "Это возможно по следующим причинам:\n\n"
                                "1) Вы неверно ввели логин или пароль.\n"
                                "2) Вы не зарегистрированы.\n"
                                "3) Ваш аккаунт ещё не одобрили.\n\n"
                                "Повторите попытку снова!"
                    }

            elif message_type == "get_cars":
                print("Обрабатываем запрос на получение данных о машинах")
                cars_data = get_car_data()
                response = {
                    "status": "success",
                    "data": cars_data
                }

            # Отправляем ответ
            response_bytes = json.dumps(response).encode('utf-8')
            conn.sendall(struct.pack('!I', len(response_bytes)))
            conn.sendall(response_bytes)

        except json.JSONDecodeError:
            print("Ошибка декодирования JSON")
            response = {"status": "error", "message": "Invalid JSON"}
            response_bytes = json.dumps(response).encode('utf-8')
            conn.sendall(struct.pack('!I', len(response_bytes)))
            conn.sendall(response_bytes)
        except Exception as e:
            print(f"Ошибка обработки запроса: {str(e)}")
            response = {"status": "error", "message": "Server error"}
            response_bytes = json.dumps(response).encode('utf-8')
            conn.sendall(struct.pack('!I', len(response_bytes)))
            conn.sendall(response_bytes)