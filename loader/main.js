// 겨울나무 AFTER 한국어 패치 로더
// Electron 은 resources/app 폴더를 app.asar 보다 먼저 읽는다.
// 원본 app.asar 는 그대로 두고, patch/ 에 있는 파일만 덮어서 보여준다.
const { app, protocol } = require('electron');
const path = require('path');
const fs = require('fs');

const ORIG = path.join(__dirname, '..', 'app.asar');
const PATCH = path.join(__dirname, 'patch');
const LOG = process.env.KOPATCH_LOG;

// 스팀 오버레이(스크린샷·녹화)가 Electron 창에 붙도록:
// GPU 를 메인 프로세스에서 돌리고 DirectComposition 을 끈다. ready 전에 해야 한다.
app.commandLine.appendSwitch('in-process-gpu');
app.commandLine.appendSwitch('disable-direct-composition');

app.on('ready', () => {
  protocol.interceptFileProtocol('file', (req, cb) => {
    let p = decodeURIComponent(new URL(req.url).pathname);
    if (process.platform === 'win32') p = p.replace(/^\/+/, '');
    p = path.normalize(p);
    const pre = ORIG.toLowerCase() + path.sep;
    if (p.toLowerCase().startsWith(pre)) {
      const cand = path.join(PATCH, p.slice(pre.length));
      if (fs.existsSync(cand)) {
        if (LOG) fs.appendFileSync(LOG, 'PATCH ' + cand + '\n');
        return cb(cand);
      }
    }
    cb(p);
  });
});

require(path.join(ORIG, 'main.js'));
