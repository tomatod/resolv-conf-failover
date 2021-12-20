# resolv-conf-failover
This is tool for failover of "nameserver" in /etc/resolv.conf

## Example
```
# before
nameserver 1.2.3.4    <= if no response 
nameserver 8.8.8.8

# after
nameserver 8.8.8.8    <= primary dns is replaced.
nameserver 1.2.3.4
```

## Require
The following python package is required.
- pyyaml
- dnspython
- pyinstaller (if you build binary)

## Get start
- If you run this script by python command.
```
git clone https://github.com/tomatod/resolv-conf-failover
cd resolv-conf-failover
sudo python3 resolv-conf-failover.py
```

- If you build binary, please run next command.
```
git clone https://github.com/tomatod/resolv-conf-failover
cd resolv-conf-failover
sudo chmod +x build-by-pyinstaller.sh
./build-by-pyinstaller.sh
```

## Configure file 
Configure file is resolv-conf-failover-config.yml. That has simple parameters
