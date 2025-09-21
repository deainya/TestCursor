import streamlit as st
import requests
import json
import re
from datetime import datetime
import os

# Настройка страницы для мобильной версии
st.set_page_config(
    page_title="Запрос на обслуживание",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS для мобильной версии
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        max-width: 80%;
    }
    
    .user-message {
        background-color: #007bff;
        color: white;
        margin-left: auto;
        text-align: right;
    }
    
    .assistant-message {
        background-color: #f8f9fa;
        color: black;
        margin-right: auto;
    }
    
    .email-input {
        margin-bottom: 2rem;
    }
    
    .problem-summary {
        background-color: #e9ecef;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    @media (max-width: 768px) {
        .main > div {
            padding: 1rem;
        }
        
        .chat-message {
            max-width: 90%;
        }
    }
</style>
""", unsafe_allow_html=True)

def validate_email(email):
    """Валидация email адреса"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def send_to_n8n(message, chat_history, problem_data):
    """Отправка данных в n8n"""
    n8n_url = os.getenv('N8N_WEBHOOK_URL')
    
    if not n8n_url:
        return {"error": "N8N_WEBHOOK_URL не настроен"}
    
    payload = {
        "message": message,
        "chat_history": chat_history,
        "problem_data": problem_data
    }
    
    try:
        response = requests.post(
            n8n_url,
            json=payload,
            timeout=30,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Ошибка сервера: {response.status_code}"}
            
    except requests.exceptions.Timeout:
        return {"error": "Таймаут соединения с n8n"}
    except requests.exceptions.ConnectionError:
        return {"error": "Ошибка подключения к n8n"}
    except Exception as e:
        return {"error": f"Неожиданная ошибка: {str(e)}"}

def display_chat_message(content, is_user):
    """Отображение сообщения в чате"""
    css_class = "user-message" if is_user else "assistant-message"
    st.markdown(f'<div class="chat-message {css_class}">{content}</div>', unsafe_allow_html=True)

def display_problem_summary(problem_data):
    """Отображение сводки по проблеме"""
    st.markdown("### 📋 Сводка по проблеме:")
    
    summary_data = []
    if problem_data.get('equipment_type'):
        summary_data.append(f"**Тип оборудования:** {problem_data['equipment_type']}")
    if problem_data.get('device_number'):
        summary_data.append(f"**Номер устройства:** {problem_data['device_number']}")
    if problem_data.get('description'):
        summary_data.append(f"**Описание проблемы:** {problem_data['description']}")
    if problem_data.get('incident_date'):
        summary_data.append(f"**Дата инцидента:** {problem_data['incident_date']}")
    if problem_data.get('photo_url'):
        summary_data.append(f"**Фото:** {problem_data['photo_url']}")
    
    if summary_data:
        st.markdown('<div class="problem-summary">' + '<br>'.join(summary_data) + '</div>', unsafe_allow_html=True)
    else:
        st.info("Информация о проблеме еще не собрана")

def main():
    st.title("🔧 Запрос на обслуживание")
    
    # Инициализация session state
    if 'email' not in st.session_state:
        st.session_state.email = None
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'problem_data' not in st.session_state:
        st.session_state.problem_data = {}
    if 'show_summary' not in st.session_state:
        st.session_state.show_summary = False
    
    # Ввод email
    if not st.session_state.email:
        st.markdown("### 📧 Введите ваш email для продолжения")
        email = st.text_input("Email:", placeholder="example@company.com", key="email_input")
        
        if st.button("Продолжить", type="primary"):
            if email and validate_email(email):
                st.session_state.email = email
                st.rerun()
            else:
                st.error("Пожалуйста, введите корректный email адрес")
    else:
        # Отображение email и кнопка смены
        col1, col2 = st.columns([3, 1])
        with col1:
            st.success(f"✅ Выполнен вход как: {st.session_state.email}")
        with col2:
            if st.button("Сменить email"):
                st.session_state.email = None
                st.session_state.chat_history = []
                st.session_state.problem_data = {}
                st.session_state.show_summary = False
                st.rerun()
        
        # Чат интерфейс
        st.markdown("### 💬 Чат с ассистентом")
        
        # Отображение истории чата
        for message in st.session_state.chat_history:
            display_chat_message(message['content'], message['is_user'])
        
        # Отображение сводки по проблеме
        display_problem_summary(st.session_state.problem_data)
        
        # Проверка на готовность к отправке
        required_fields = ['equipment_type', 'device_number', 'description', 'incident_date']
        missing_fields = [field for field in required_fields if not st.session_state.problem_data.get(field)]
        
        if not missing_fields and not st.session_state.show_summary:
            st.session_state.show_summary = True
            st.rerun()
        
        # Форма ввода сообщения
        if not st.session_state.show_summary:
            user_input = st.text_input("Введите ваше сообщение:", placeholder="Опишите проблему...", key="user_input")
            
            if st.button("Отправить", type="primary") and user_input:
                # Добавляем сообщение пользователя в историю
                st.session_state.chat_history.append({
                    "content": user_input,
                    "is_user": True
                })
                
                # Отправляем в n8n
                with st.spinner("Обработка запроса..."):
                    response = send_to_n8n(
                        user_input,
                        st.session_state.chat_history,
                        st.session_state.problem_data
                    )
                
                if "error" in response:
                    st.error(f"Ошибка: {response['error']}")
                else:
                    # Обновляем данные проблемы
                    if 'problem_data' in response:
                        st.session_state.problem_data.update(response['problem_data'])
                    
                    # Добавляем ответ ассистента
                    if 'response' in response:
                        st.session_state.chat_history.append({
                            "content": response['response'],
                            "is_user": False
                        })
                
                st.rerun()
        
        # Отображение итогового запроса и подтверждение
        if st.session_state.show_summary:
            st.markdown("### ✅ Итоговый запрос на обслуживание")
            
            # Отображение всех собранных данных
            st.markdown("**Email:** " + st.session_state.email)
            display_problem_summary(st.session_state.problem_data)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Подтвердить отправку", type="primary"):
                    # Отправляем финальный запрос
                    with st.spinner("Отправка запроса..."):
                        final_response = send_to_n8n(
                            "done-request",
                            st.session_state.chat_history,
                            st.session_state.problem_data
                        )
                    
                    if "error" in final_response:
                        st.error(f"Ошибка отправки: {final_response['error']}")
                    else:
                        st.success("✅ Запрос успешно отправлен!")
                        
                        # Очищаем данные
                        st.session_state.chat_history = []
                        st.session_state.problem_data = {}
                        st.session_state.show_summary = False
                        st.rerun()
            
            with col2:
                if st.button("🔄 Продолжить диалог"):
                    st.session_state.show_summary = False
                    st.rerun()

if __name__ == "__main__":
    main()
