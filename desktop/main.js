const { app, BrowserWindow, shell } = require('electron');
const path = require('node:path');
function createWindow(){const win=new BrowserWindow({width:1120,height:900,minWidth:720,minHeight:640,backgroundColor:'#202421',autoHideMenuBar:true,webPreferences:{preload:path.join(__dirname,'preload.js'),contextIsolation:true,nodeIntegration:false}});win.loadFile('index.html');win.webContents.setWindowOpenHandler(({url})=>{shell.openExternal(url);return {action:'deny'};});}
app.whenReady().then(()=>{createWindow();app.on('activate',()=>{if(BrowserWindow.getAllWindows().length===0)createWindow();});});
app.on('window-all-closed',()=>{if(process.platform!=='darwin')app.quit();});
