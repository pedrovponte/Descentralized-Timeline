# Project t2-g15

## Install Dependencies

Inside *doc* folder run command:

> pip install -t requirements.txt

OR

Separately run commands:

```
pip install kadamlia==2.2.2
pip install ntplib==0.4.0
```

----

## Run program

Inside *src* folder:

* To initiate the start bootstrap nodes, in one terminal run:
    * **Windows:** ```py initial_peers.py```
    * **Linux:** ```python3 initial_peers.py```

* Then to initiate a user run in another terminal:
    * **Windows:** ```py peer.py <port>```
    * **Linux:** ```python3 peer.py <port>```
