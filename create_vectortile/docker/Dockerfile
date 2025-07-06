FROM ubuntu:20.04

SHELL ["/bin/bash", "-c"]

RUN apt-get update -y
RUN apt-get upgrade -y
RUN apt-get install -y python3.8 python3.8-dev
RUN source ~/.bashrc
RUN apt-get -y install vim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

#その他　必要そうなもの
RUN apt-get install -y --no-install-recommends wget build-essential libreadline-dev \ 
libncursesw5-dev libssl-dev libbz2-dev liblzma-dev zlib1g-dev net-tools

RUN apt-get install -y curl 
RUN curl -k https://bootstrap.pypa.io/get-pip.py -o get-pip.py
RUN apt-get install -y python3.8-distutils
RUN apt-get install -y libffi-dev python-dev python3-dev libpq-dev

RUN apt-get install -y libgeos-dev libproj-dev gdal-bin libgdal-dev
RUN apt-get install -y python3-gdal

# tippecanoeインストールに必要なgitとmake
RUN apt-get update -y
RUN apt-get install git -y -o Acquire::http::Proxy=$http_proxy -o Acquire::https::Proxy=$https_proxy --fix-missing
RUN apt-get -y install gcc g++ make libsqlite3-dev zlib1g-dev

# gitからtippecanoeをclone
RUN git clone https://github.com/felt/tippecanoe.git

# コンテナ起動時に実行するシェル（tippecanoeのインストール&シェルセッション起動）をコピー
COPY container_startup.sh /home/
RUN chmod +x /home/container_startup.sh

# サイズ削減のため不要なものは削除
RUN apt-get autoremove -y

RUN python3.8 get-pip.py
RUN pip install -U pip
# Pipのアップデート
RUN pip install --upgrade pip 
# requirements.txtでインストール
COPY ./requirements.txt . 
RUN pip install -r ./requirements.txt

# コンテナ起動時にシェルを起動
CMD /home/container_startup.sh