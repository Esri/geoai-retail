from pathlib import Path

data = Path('./data').absolute()
interim = data/'interim'
raw = data/'raw'
for dir in [data, interim, raw]:
    if not dir.exists():
        dir.mkdir(parents=True)
interim_gdb = interim/'interim.gdb'
raw_gdb = raw/'raw.gdb'
