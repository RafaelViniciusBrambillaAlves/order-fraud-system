#!/bin/bash

mongod --replSet rs0 --bind_ip_all &
pid=$!

echo "Waiting MongoDB start..."

until mongosh --quiet --eval "db.adminCommand({ ping: 1 })" >/dev/null 2>&1
do
  sleep 1
done

echo "Initializing replica set..."

mongosh --quiet --eval "
try {
  rs.status()
} catch(e) {
  rs.initiate({
    _id: 'rs0',
    members: [{ _id: 0, host: 'mongodb:27017' }]
  })
}
"

echo "Waiting PRIMARY election..."

until mongosh --quiet --eval "rs.isMaster().ismaster" | grep -q true
do
  sleep 1
done

echo "Mongo PRIMARY ready."

wait $pid