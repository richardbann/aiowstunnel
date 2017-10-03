import React from 'react';
import ReactDOM from 'react-dom';
import './index.css';
import App from './App';
// import registerServiceWorker from './registerServiceWorker';

ReactDOM.render(<App wsURI="wss://tunnel.vertis.com/stats" />, document.getElementById('root'));
// registerServiceWorker();
