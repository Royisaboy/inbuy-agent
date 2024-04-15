FROM python:3.11
WORKDIR /app
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt /app/requirements.txt
RUN pip3 install -r requirements.txt
COPY . /app
CMD ["python3", "run.py"]