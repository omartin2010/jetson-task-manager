## Task Detection
In order to start the daemon, you need to run this command; this will ensure that after reboots, it starts automatically.
```
docker run --restart unless-stopped --privileged -d \
    --name taskmanager \
    --memory 0.5g \
    --network host \
    --log-driver json-file --log-opt max-size=500k
    taskmanager:latest
```