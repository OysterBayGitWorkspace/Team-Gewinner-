# Weekly schedule (launchd, this Mac)

Runs `run.py` every Monday at 07:00 local time and leaves the dashboard in `out/`.

```bash
sed "s#__REPO__#$(pwd)#g" schedule/vc.oysterbay.pulse.plist > ~/Library/LaunchAgents/vc.oysterbay.pulse.plist
launchctl unload ~/Library/LaunchAgents/vc.oysterbay.pulse.plist 2>/dev/null
launchctl load ~/Library/LaunchAgents/vc.oysterbay.pulse.plist
launchctl start vc.oysterbay.pulse     # run once now to verify
tail -f schedule/pulse.log
```

Failure behaviour: exit code 2 (auth or inventory) is written to `schedule/pulse.log` with the fix. There is no silent success: a run that produced no `out/index.html` newer than the log line failed.

Known limit: a closed laptop skips the run. See TODOS.md P1.
