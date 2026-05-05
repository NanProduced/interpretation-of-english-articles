const fs = require('fs');
let content = fs.readFileSync('c:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/components/ParagraphBlock/index.scss', 'utf8');

// Strip comments
content = content.replace(/\/\*[\s\S]*?\*\/|([^:]|^)\/\/.*/g, '$1');

let stack = [];
let lines = content.split('\n');

for (let i = 0; i < lines.length; i++) {
  let line = lines[i];
  for (let j = 0; j < line.length; j++) {
    if (line[j] === '{') {
      stack.push({ line: i + 1, char: j + 1 });
    } else if (line[j] === '}') {
      if (stack.length === 0) {
        console.log(`Extra } at line ${i + 1}, char ${j + 1}`);
      } else {
        stack.pop();
      }
    }
  }
}

if (stack.length > 0) {
  stack.forEach(s => console.log(`Unclosed { at line ${s.line}, char ${s.char}`));
} else {
  console.log('Braces are balanced (comments ignored)');
}
