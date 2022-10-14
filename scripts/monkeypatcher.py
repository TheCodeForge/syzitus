import gevent.monkey
print("monkeypatching")
gevent.monkey.patch_all()
print("done")