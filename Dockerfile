FROM python:3.12-alpine3.21 AS builder
WORKDIR /app
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install -r requirements.txt

FROM alpine:3.21 AS wg
RUN apk add --no-cache wireguard-tools bash

FROM python:3.12-alpine3.21 
WORKDIR /app
COPY --from=builder /app/venv ./venv
COPY --from=wg /usr/bin/wg /usr/bin/wg
COPY --from=wg /bin/bash /bin/bash
COPY --from=wg /lib/ld-musl-x86_64.so.1 /lib/ld-musl-x86_64.so.1
COPY --from=wg /usr/lib/libreadline.so.8 /usr/lib/libreadline.so.8
COPY --from=wg /usr/lib/libncursesw.so.6 /usr/lib/libncursesw.so.6
COPY . .
RUN chown -R 1020:1020 *
USER 1020
ENV PATH="/app/venv/bin:$PATH"
CMD ["python3", "bot.py"]