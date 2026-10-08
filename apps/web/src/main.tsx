import React from 'react'
import ReactDOM from 'react-dom/client'
import { App } from './App'
import { AppStore } from './store'
import './styles.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><App store={new AppStore()} /></React.StrictMode>,
)
