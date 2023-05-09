FROM python:3.10

ENV PYTHONUNBUFFERED 1

RUN apt-get update
RUN apt-get upgrade -y
RUN apt remove docker docker.io containerd runc
RUN apt-get install --no-install-recommends -y pkg-config build-essential ca-certificates curl gnupg
RUN install -m 0755 -d /etc/apt/keyrings
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
RUN chmod a+r /etc/apt/keyrings/docker.gpg
RUN echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian bullseye stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null
RUN apt update
RUN apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# RUN apt-get update && \
#     apt-get upgrade -y && \
#     apt-get install --no-install-recommends -y pkg-config build-essential remove docker docker-engine docker.io containerd runc && \
#     apt-get autoremove -y && \
#     apt-get clean all && \
#     rm -rf /var/lib/apt/lists/* && \
#     pip --no-cache-dir install --upgrade pip wheel

RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="${PATH}:/root/.local/bin"
RUN poetry config virtualenvs.create false

RUN pip install toml invoke