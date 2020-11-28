# firewall-ui
This set of scripts provides a simple secure web based UI to iptables rules.

I needed a web UI to handle turning on and off certain rules.  I run a router with a specific set of
iptables rules, and I needed a web UI that wouldn't also compromise it's security.  I started with a model
of a elevated permissions script doing the iptables work, and for communication with it use a "semaphore"
directory where files are created or deleted in order to activate it.  A second script which is the UI 
does the creating or deleting of those files, and also shows the status based on this directory.

No direct access to the subprocess call.  No access to a daemon running as root on a network port.

To run it: 

- create a chain that you will use.  Or don't, but either way you will need to specify the chain name in the rules file.
- use the serverStartScript.  Edit it to have the right location of the files, and place it in /etc/cron.hourly.  This will start the server process using screen.  I do this on other python services that I have created because it allows me to monitor it real time.  It isn't completely necessary though and in the future i may add files to use with systemd.



