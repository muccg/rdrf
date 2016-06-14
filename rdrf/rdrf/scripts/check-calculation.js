#!/usr/bin/env node

// Uses JSlint to check javascript against Crockford's ADsafe language subset.
// The script under test is provided on stdin.
// Errors on stdout, one per line.

var fs = require("fs");
var vm = require("vm");
var path = require("path");

function main() {
  // Load jslint. It has to be the version from 2013-02-03 because
  // ADsafe was removed in subsequent versions.
  var JSLINT = loadFile(path.resolve(__dirname, "jslint.js")).JSLINT;

  // Script on standard input, surround in adsafe widget.
  var text = fs.readFileSync(/*process.stdin.fd*/ "/dev/stdin");
  var fragment = [].concat(fragmentHeader, [text], fragmentFooter).join("\n");

  var res = JSLINT(fragment, {
    adsafe: true,
    fragment: true,
    unparam: true,
    vars: true,
    white: true
  });

  if (!res) {
    var data = JSLINT.data();
    data.errors.forEach(function(error) {
      if (error) {
        // offset line numbers by preamble length
        if (error.line) {
          error.line -= fragmentHeader.length;
        }
        // "ADsafe" is confusing in this context, rename it
        if (error.reason) {
          error.reason = error.reason.replace("ADsafe", "Safety");
        }
      }
    });

    // html report
    // var myReport = JSLINT.error_report(data);
    // console.log(myReport);

    data.errors.forEach(function(error) {
      if (error && error.line && error.reason) {
        console.log("line " + error.line + ": " + error.reason);
      }
    });
  }

  return res ? 0 : 1;
}

var fragmentHeader = [
  '<div id="TEST_">',
  '<script>',
  'ADSAFE.go("TEST_", function (dom, lib) {',
  '  "use strict";',
  '  var context = {}, patient = {}, Date = {}, RDRF = {};',
  '  // begin input'
];

var fragmentFooter = [
  '  // end input',
  '});',
  '</script>',
  '</div>'
];


/**
 * Loads javascript code which isn't a nodejs module.
 * http://stackoverflow.com/a/8808162
 */
function loadFile(path, context) {
  context = context || {};
  var data = fs.readFileSync(path);
  vm.runInNewContext(data, context, path);
  return context;
}

process.exit(main());
