# encoding: utf-8
#
#   Custom routing Router to Mama (ROUTER to REQ)
#
#   Author: Jeremy Avnet (brainsik) <spork(dash)zmq(at)theory(dot)org>
#

import time
import random
from threading import Thread
import pickle

import zmq

import zhelpers
try:
    import zeppy.z_runners as z_runners
except ModuleNotFoundError as e:
    import z_runners



NBR_WORKERS = 3


def worker_thread(context=None):
    context = context or zmq.Context.instance()
    worker = context.socket(zmq.REQ)

    # We use a string identity for ease here
    zhelpers.set_id(worker)
    worker.connect("tcp://localhost:5671")

    total = 0
    while True:
        # Tell the router we're ready for work
        worker.send(b"ready")

        # Get workload from router, until finished
        workload = worker.recv()
        try:
            fname, idftxt, wfiletxt, getdict = pickle.loads(workload)
        except pickle.UnpicklingError as e:
            pass
        finished = workload == b"END"
        if finished:
            print("Processed: %d tasks" % total)
            break
        total += 1

        # Do some random work
        fullresult = z_runners.zeppy_runandget(idftxt, wfiletxt, getdict)
        time.sleep(0.1 * random.random())


context = zmq.Context.instance()
client = context.socket(zmq.ROUTER)
client.bind("tcp://*:5671")

for _ in range(NBR_WORKERS):
    Thread(target=worker_thread).start()

fnames = [
    "1ZoneEvapCooler.idf",
    "1ZoneUncontrolled_DD2009.idf",
    "1ZoneUncontrolled_DDChanges.idf",
    ]
wfile = "/Applications/EnergyPlus-9-3-0/WeatherData/USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw"
getdict = dict(
    twocells=dict(
        whichfile="htm",
        tablename="Site and Source Energy", 
        cells=[[-2, 1], [-2, -2]],  # will return 2 cells
    ),
)
for fname in fnames:
    idfname = f'/Applications/EnergyPlus-9-3-0/ExampleFiles/{fname}'
    idftxt, wfiletxt = z_runners.to_zeppy_runandget(idfname, wfile)
    message = pickle.dumps((fname, idftxt, wfiletxt, getdict))
    # LRU worker is next waiting in the queue
    address, empty, ready = client.recv_multipart()

    client.send_multipart([
        address,
        b'',
        message,
    ])

# Now ask mama to shut down and report their results
for _ in range(NBR_WORKERS):
    address, empty, ready = client.recv_multipart()
    client.send_multipart([
        address,
        b'',
        b'END',
    ])