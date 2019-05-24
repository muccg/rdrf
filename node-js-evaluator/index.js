const express = require('express');
let bodyParser = require('body-parser');
const process = require('process');
const app = express();
const port = 3131;

app.use(bodyParser.json());
app.use(bodyParser.urlencoded({extended: true}));

app.post('/eval', (req, res) => {
    const code_to_eval = "try { " + decodeURIComponent(req.body.jscode) + "} catch (e) {console.log(e); res.send(JSON.stringify(\"\"));}";
    res.send(JSON.stringify(eval(code_to_eval)));
});

app.listen(port, () => console.log(`JS Evaluator listening on port ${port}!`));

// handle stop signal so we can close docker container quickly instead to wait for it to kill the node process.
process.on('SIGTERM', () => {
    app.close(() => {
        process.exit(0);
    });
});
