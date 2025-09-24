# Архивировано
## Установка Python
**Установить:** Python 3.10  
**Поставить галочку при установке:** Add Python to Path  

## Установка и Запуск
**Git:** git clone https://github.com/FreshLend/FreshTube.git  
**Выполнить:** pip install -r requirements.txt  
**Можно запускать:** python app.py  

## Настройка
**необходио настроить некоторые параметры в app.py**  
в начале, устанвить максимальный размер загрузки видео, заменить секретный ключ.  
```py
app.config['MAX_CONTENT_LENGTH'] = 8192 * 1024 * 1024 # 8GB максимум для загрузки видео
app.config['SECRET_KEY'] = 'your-secret-key' # заменить
```
и в конце, выбрать нужный порт  
```py
app.run(host='0.0.0.0', port=5000, debug=True)
```
