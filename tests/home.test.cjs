const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const context = {};
vm.createContext(context);
vm.runInContext(fs.readFileSync('app/backgrounds.js', 'utf8'), context);
const choose = context.homeBackgroundForDate;
assert.equal(choose(new Date(2026, 10, 17, 0)).file, choose(new Date(2026, 10, 17, 23, 59)).file);
assert.notEqual(choose(new Date(2026, 10, 17)).file, choose(new Date(2026, 10, 18)).file);
assert.equal(choose(new Date(2026, 10, 17)).file, choose(new Date(2026, 10, 24)).file);
for (const [y, m, d] of [[2026, 2, 7], [2026, 9, 31], [2028, 1, 28], [2026, 11, 31]]) {
  assert.notEqual(choose(new Date(y, m, d)).file, choose(new Date(y, m, d + 1)).file);
}
let now = 100, calls = [];
const filter = {
  Date: {now: () => now}, Qt: {Key_Super_L: 1}, KeyPolicy: {NextPolicy: 0, Accepted: 1},
  applicationManager: {launch: id => calls.push(id)}
};
vm.createContext(filter);
vm.runInContext(fs.readFileSync('tv/home/home-keyfilter.js', 'utf8'), filter);
assert.equal(filter.handleMinimalHome(2, true, false), 0);
filter.handleMinimalHome(1, true, false); now += 100;
assert.equal(filter.handleMinimalHome(1, false, false), 1);
assert.equal(calls.pop(), 'org.example.minimalhome');
filter.handleMinimalHome(1, true, false); now += 1600;
filter.handleMinimalHome(1, false, false);
assert.equal(calls.pop(), 'com.webos.app.home');
filter.applicationManager.launch = () => { throw Error('simulated failure'); };
assert.equal(filter.handleMinimalHome(1, false, false), 0);
console.log('Calendar rotation and Home-key routing passed.');
