from subprocess import call
import myconfig

blobpath='upload/data'
localpath='data'

call(["blobxfer", "upload", "--storage-account", myconfig.blobacct, "--storage-account-key", myconfig.blobkey, "--remote-path", blobpath, "--local-path", localpath, "--skip-on-lmt-ge"])
