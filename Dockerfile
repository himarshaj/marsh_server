FROM    python:3.6

LABEL   maintainer="Himarsha Jayanetti"

RUN     pip install pyyaml validators

ENV     PYTHONUNBUFFERED=1
ENV     DOCROOT=/var/www/marshserver
ENV     LOG_DIR=/var/www/marshserver/log

ADD     sample/* $DOCROOT/
ADD     log/* $LOG_DIR/

WORKDIR /app
COPY    template ./template
COPY    src ./src
COPY    log ./log
RUN     chmod +x src/*.py

CMD     ["src/marshserver.py", "0.0.0.0", "80"]
