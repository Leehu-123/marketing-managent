const fs = require('fs');
const html = fs.readFileSync('f:/Antigrapvity/SEO Website DAFA web/backend/templates/production.html', 'utf8');

// The x-data starts at line 20: `<div x-data="{`
// The x-data ends at line 537: `}" class="grid...`

const match = html.match(/x-data="(\{[\s\S]*?\})"/);
if (match) {
    const jsCode = match[1];
    try {
        new Function('return ' + jsCode);
        console.log("Syntax is VALID!");
    } catch (e) {
        console.log("Syntax ERROR:", e.message);
        // Find the line number of the error
        // A naive way is to write the code to a file and run it
        fs.writeFileSync('temp.js', 'const x = ' + jsCode + ';');
    }
} else {
    console.log("x-data not found or regex failed!");
}
