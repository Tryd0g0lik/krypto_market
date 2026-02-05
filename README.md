Note: Публикация файлов не нарушило условий задания 
## APP CryptoMarket
 


[![project_model.drawio.svg](img/project_model.drawio.png)](img/project_model.drawio_max.png)



Person чтоб платформа не:
     - зависила от от пользователей,
     - и не несла ответственности за действия пользователей


<<<<<<< HEAD
Данные об успешной авторизации кешируем на 27 часов. и сразу отправляю сообщение по SSE/ D cjj,otybb токены.

=======
Промежуточная функция перехватывает данные полльзователя и шифрует секретный клю. После этот ключ отправляется в кеш. 
Уже из кеша , когда получаем этот ключ (в одной из задачи) то де-шифровка секретного текста для аутентификации пользователя.


Данные об успешной авторизации кешируем на 27 часов. и сразу отправляю сообщение по SSE. В сообщении токены.


args = ("btc_usd", "eth_usd", "connection")
ServerSSEManager(args) на старте получает kricers.  

Каждый пользователь имеет разовый уникальный ключь шифра на время жизни секретных данных. 
Ключи это результат генератора. 

parrameter: 'url/?timer=5' Пользователь устанавливает время в секундах. Время для \
временного интервала (обновления данных). По умолчанию 60 секунд

Authentication https://docs.deribit.com/articles/authentication \
```text

{
    "jsonrpc": "2.0",
    "id": 9929,
    "method": "public/auth",
    "params": {
        "grant_type": "client_credentials",
        "client_id": "_XcQ7xuV",
        "client_secret": "pc4eqeiEYnj3TecFPjBXb_XfWD3uq_PHvXrFW2-PKQY"
    }
}


{
    "id": 5647,
    "method": "private/get_subaccounts",
    "params": {
        "access_token": "1801724331883.1Qp6xvSi.MOfODO-DpDBgIFX6rWKeoxJHowl7Al8wa2GSvOdlimFXQ8-yR6gViXR8VRC3eJlbL2dTFmbXtilDQ4qWXlYDKi8ndyo83WijEb3oel3JNVLLmZqNHPYoxvTsWMM-pCURrDKrPiJK0nsk-PuAorqHNDPg2tlQ0y_C6q53BOyPk4K6ee7aCwHT-5-J_dhcSICeZdoQ1vbqgOBh4ywaAa2SVmQd4h56ik0P_UJ7S3JhMRJMWHLhBXqt5pc3fngpCSYmuvSAX5uTGcOuJaEcSCmbwtuJkxDUn6OMdyRxNXxj7lQI-GgxUy04CjupP8KN2tv5pgxvfmL0l06JSJiTg2HJcfUVAIU4icZX8LB09IBB7hcqv6s"
    }
}


{
    "jsonrpc": "2.0",
    "id": 1234,
    "method": "public/get_index_price",
    "params": {
        "index_name": "btc_usd"
    }
}

```


----


Мы знаем - Полиморфизм. Но это в ООП. Тут же говорю о целом APP. Стараюсь делать единый код для выполнения разных задач \
Изменения только в args/kwargs
>>>>>>> dev
