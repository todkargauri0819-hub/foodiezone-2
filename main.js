const { app, BrowserWindow } = require('electron')

function createWindow () {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    icon: 'logo.png',   // your app logo
    webPreferences: {
      nodeIntegration: false
    }
  })

  win.loadURL('http://127.0.0.1:5000') // FoodieZone URL
}

app.whenReady().then(createWindow)
