const http = require('http');
const archive = Buffer.from('UEsDBBQAAAAAAIWUZ13HoBgEDwAAAA8AAAAKAAAAcmVjb3JkLmZpdAwQAAABAAAALkZJVADP+1BLAQIUAxQAAAAAAIWUZ13HoBgEDwAAAA8AAAAKAAAAAAAAAAAAAACAAQAAAAByZWNvcmQuZml0UEsFBgAAAAABAAEAOAAAADcAAAAAAA==', 'base64');

http.createServer((req, res) => {
  const url = new URL(req.url, 'http://localhost');
  const tokenPath = '/personalapitoken-service/personal-api/personal-api-key/token';
  if (req.method === 'POST' && url.pathname === tokenPath) {
    const status = req.headers.authorization === 'ApiKey rate-limited-key' ? 429 :
      req.headers.authorization === 'ApiKey test-key' ? 200 : 401;
    res.writeHead(status, { 'Content-Type': 'text/plain' });
    return res.end(status === 200 ? 'test-bearer-token' : 'Denied');
  }
  if (req.headers.authorization !== 'Bearer test-bearer-token') {
    res.writeHead(401);
    return res.end();
  }
  if (req.method === 'GET' && url.pathname === '/activitylist-service/activities/search/activities') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    return res.end(JSON.stringify(Number(url.searchParams.get('start')) === 0 ? [{ activityId: 123 }] : []));
  }
  if (req.method === 'GET' && url.pathname === '/activity-service/activity/123') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    return res.end(JSON.stringify({ activityId: 123 }));
  }
  if (req.method === 'GET' && url.pathname === '/download-service/files/activity/123') {
    res.writeHead(200, { 'Content-Type': 'application/x-zip-compressed' });
    return res.end(archive);
  }
  res.writeHead(404);
  res.end();
}).listen(process.env.PORT || 4500);
