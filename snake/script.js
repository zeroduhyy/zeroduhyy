// Simple Snake game using canvas. Grid-based logic with smooth animation.
// Controls: Arrow keys or WASD. Space to pause/resume. Restart button provided.

const canvas = document.getElementById('game');
const ctx = canvas.getContext('2d');
const scoreEl = document.getElementById('score');
const restartBtn = document.getElementById('restart');

// Grid configuration
const TILE = 20; // pixels per cell
const COLS = Math.floor(canvas.width / TILE);
const ROWS = Math.floor(canvas.height / TILE);

// Game state
let snake = [{x: Math.floor(COLS/2), y: Math.floor(ROWS/2)}];
let dir = {x: 1, y: 0}; // moving right initially
let nextDir = {...dir};
let food = null;
let speed = 8; // ticks per second
let lastFrame = 0;
let accumulator = 0;
let tickInterval = 1000 / speed;
let paused = false;
let score = 0;

function placeFood(){
  while(true){
    const f = {x: Math.floor(Math.random()*COLS), y: Math.floor(Math.random()*ROWS)};
    // avoid placing on snake
    if(!snake.some(s => s.x===f.x && s.y===f.y)){
      food = f; return;
    }
  }
}

function reset(){
  snake = [{x: Math.floor(COLS/2), y: Math.floor(ROWS/2)}];
  dir = {x:1,y:0}; nextDir = {...dir};
  score = 0; scoreEl.textContent = `Score: ${score}`;
  speed = 8; tickInterval = 1000/speed;
  placeFood();
  paused = false;
}

function update(){
  // apply nextDir (prevents reversing)
  if((nextDir.x !== -dir.x || nextDir.y !== -dir.y) ) dir = nextDir;

  // new head
  const head = {x: (snake[0].x + dir.x + COLS) % COLS, y: (snake[0].y + dir.y + ROWS) % ROWS};

  // collision with self?
  if(snake.some(s => s.x === head.x && s.y === head.y)){
    // game over -> restart after short flash
    paused = true;
    flashGameOver();
    return;
  }

  snake.unshift(head);

  // ate food?
  if(food && head.x === food.x && head.y === food.y){
    score += 1;
    scoreEl.textContent = `Score: ${score}`;
    // increase speed slightly every 4 points
    if(score % 4 === 0) { speed = Math.min(20, speed + 1); tickInterval = 1000/speed; }
    placeFood();
  } else {
    snake.pop();
  }
}

function draw(){
  // clear
  ctx.fillStyle = '#081018';
  ctx.fillRect(0,0,canvas.width,canvas.height);

  // grid (subtle)
  ctx.strokeStyle = 'rgba(255,255,255,0.02)';
  ctx.lineWidth = 1;
  for(let x=0;x<=COLS;x++){
    ctx.beginPath(); ctx.moveTo(x*TILE,0); ctx.lineTo(x*TILE,canvas.height); ctx.stroke();
  }
  for(let y=0;y<=ROWS;y++){
    ctx.beginPath(); ctx.moveTo(0,y*TILE); ctx.lineTo(canvas.width,y*TILE); ctx.stroke();
  }

  // draw food
  if(food){
    ctx.fillStyle = '#ff6b6b';
    roundRect(ctx, food.x*TILE+2, food.y*TILE+2, TILE-4, TILE-4, 4, true, false);
  }

  // draw snake
  for(let i=0;i<snake.length;i++){
    const s = snake[i];
    const t = i === 0 ? '#00e5ff' : `rgba(0,213,255,${1 - i/snake.length*0.6})`;
    ctx.fillStyle = t;
    roundRect(ctx, s.x*TILE+1, s.y*TILE+1, TILE-2, TILE-2, 4, true, false);
  }
}

function loop(now){
  if(!lastFrame) lastFrame = now;
  const dt = now - lastFrame; lastFrame = now;
  if(!paused){
    accumulator += dt;
    while(accumulator >= tickInterval){
      update();
      accumulator -= tickInterval;
    }
  }
  draw();
  requestAnimationFrame(loop);
}

function flashGameOver(){
  // visual flash then reset
  const prevFill = ctx.fillStyle;
  ctx.fillStyle = 'rgba(255,40,40,0.14)';
  ctx.fillRect(0,0,canvas.width,canvas.height);
  setTimeout(()=>{
    reset();
  },600);
}

// small helper: rounded rect
function roundRect(ctx,x,y,w,h,r,fill,stroke){
  if(typeof r==='undefined') r=5;
  ctx.beginPath();
  ctx.moveTo(x+r,y);
  ctx.arcTo(x+w,y,x+w,y+h,r);
  ctx.arcTo(x+w,y+h,x,y+h,r);
  ctx.arcTo(x,y+h,x,y,r);
  ctx.arcTo(x,y,x+w,y,r);
  ctx.closePath();
  if(fill) ctx.fill();
  if(stroke) ctx.stroke();
}

// input
window.addEventListener('keydown',(e)=>{
  const key = e.key;
  if(key===' '){ paused = !paused; e.preventDefault(); return; }
  if(['ArrowUp','w','W'].includes(key)) nextDir = {x:0,y:-1};
  if(['ArrowDown','s','S'].includes(key)) nextDir = {x:0,y:1};
  if(['ArrowLeft','a','A'].includes(key)) nextDir = {x:-1,y:0};
  if(['ArrowRight','d','D'].includes(key)) nextDir = {x:1,y:0};
});

restartBtn.addEventListener('click',()=>{ reset(); });

// initialize
placeFood();
reset();
requestAnimationFrame(loop);
