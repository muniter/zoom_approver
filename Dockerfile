FROM python:3

WORKDIR /usr/src/app
VOLUME ["/usr/src/app/config"]
# Copy all the app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000/tcp

CMD ["python", "./main.py"]
