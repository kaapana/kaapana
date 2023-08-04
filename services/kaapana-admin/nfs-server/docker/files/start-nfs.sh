#!/bin/sh

# Start the required services
rpcbind
rpc.statd
rpc.nfsd

# Export the NFS shares
exportfs -r

# Keep the container running
tail -f /dev/null
