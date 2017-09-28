import React, {Component} from 'react';
// import logo from './logo.svg';
// import './App.css';

class App extends Component {
  constructor(props) {
    super(props);
    this.ws = null;
    this.nextConnIdx = 0;
    this.nextConnAt = null;
    this.timer = null;

    this.state = {
      wsState: 'CONNECTING', // CONNECTED, FAILEDRECONNECT, CLOSEDRECONNECT
      nextConnSec: null,
      data: null
    };
  }

  startReconnect() {
    this.nextConnAt =
      new Date().getTime() + 1000 * this.props.delays[this.nextConnIdx];
    this.nextConnIdx =
      this.nextConnIdx === this.props.delays.length - 1
        ? this.nextConnIdx
        : this.nextConnIdx + 1;
    this.timer = setTimeout(() => this.checkReconnect(), 100);
  }

  checkReconnect() {
    const nextConnSec = this.nextConnSec();
    if (nextConnSec === 0) {
      this.wsConnect();
    } else {
      this.timer = setTimeout(() => this.checkReconnect(), 300);
      this.setState({
        nextConnSec: nextConnSec
      });
    }
  }

  nextConnSec() {
    return Math.floor((this.nextConnAt - new Date().getTime()) / 1000);
  }

  wsConnect() {
    this.ws = new WebSocket(this.props.wsURI);
    this.ws.onopen = () => {
      this.nextConnIdx = 0;
      this.setState({
        wsState: 'CONNECTED',
        data: null
      });
    };
    this.ws.onclose = () => {
      this.startReconnect();
      this.setState({
        wsState: 'CLOSEDRECONNECT',
        nextConnSec: this.nextConnSec()
      });
    };
    this.ws.onmessage = e => {
      this.setState({data: JSON.parse(e.data)});
    };
  }

  componentDidMount() {
    this.wsConnect();
  }

  connectionRows(conns) {
    const ret = [];
    conns.map(conn => {
      ret.push(
        <tr className="conn" key={conn.id}>
          <td style={{textAlign: 'right'}}>{conn.mode}</td>
          <td>{conn.host}</td>
          <td>{conn.port}</td>
          <td>{conn.createTime}</td>
          <td colSpan={5} style={{textAlign: 'right'}}>
            {/* TODO */}
            <button data-url="/close/{{ conn.id }}">close</button>
          </td>
        </tr>
      );
      conn.connections.map(fwdconn =>
        ret.push(
          <tr key={conn.id + '|' + fwdconn.id}>
            <td style={{textAlign: 'right'}}>{fwdconn.id}</td>
            <td>{fwdconn.addr}</td>
            <td>{fwdconn.port}</td>
            <td>{fwdconn.createTime}</td>
            <td style={{textAlign: 'right'}}>{fwdconn.toSocket}</td>
            <td style={{textAlign: 'center'}}>➼</td>
            <td>socket</td>
            <td style={{textAlign: 'center'}}>➼</td>
            <td>{fwdconn.fromSocket}</td>
          </tr>
        )
      );
      return 1;
    });
    return ret;
  }

  render() {
    switch (this.state.wsState) {
      case 'CONNECTING':
        return <div className="server">connecting...</div>;
      case 'FAILEDRECONNECT':
        return (
          <div className="server">
            connection failed, reconnecting in {this.state.nextConnSec}{' '}
            seconds...
          </div>
        );
      case 'CLOSEDRECONNECT':
        return (
          <div className="server">
            connection closed, reconnecting in {this.state.nextConnSec}{' '}
            seconds...
          </div>
        );
      case 'CONNECTED':
        if (this.state.data === null)
          return <div className="server">connected, waiting for data...</div>;
        else
          return (
            <div>
              <div className="server">
                tunnel server listening on {this.state.data.host}:{' '}
                {this.state.data.port}
              </div>
              <table cellSpacing="0">
                <tbody>
                  {this.connectionRows(this.state.data.connections)}
                </tbody>
              </table>
            </div>
          );
      default:
        return (
          <div className="server">invalid state: {this.state.wsState}</div>
        );
    }
  }
}

App.defaultProps = {
  wsURI: 'wss://localhost/stats',
  delays: [5, 5, 5, 10]
};

export default App;
