// This file watch if any change happens in the frontend folder and
// rebuild the production build. It is the current behaviour of our React development.
// Obviously it is not as great as using yarn start using the create-react-app node server which provide a development build
// with additional warnings. 

const watch = require('watch');
const { exec } = require('child_process');

function run_yarn_build() {
    exec('yarn build', (err, stdout, stderr) => {
        if (err) {
            // node couldn't execute the command
            console.log(err)
            return;
        }

        // the *entire* stdout and stderr (buffered)
        console.log(`stdout: ${stdout}`);
        console.log(`stderr: ${stderr}`);
    });
}

// Watch if any file is changed.
watch.watchTree('./src', function (f, curr, prev) {
    if (typeof f == "object" && prev === null && curr === null) {
        // Finished walking the tree
    } else if (prev === null) {
        // f is a new file
        console.log("NEW FILE")
        run_yarn_build()
    } else if (curr.nlink === 0) {
        // f was removed
        console.log("FILE DELETED")
        run_yarn_build()
    } else {
        // f was changed
        console.log("FILE UPDATED")
        run_yarn_build()
    }
})

