import React, {Component} from 'react';
// import logo from './logo.svg';
// import './App.css';

class App extends Component {
  constructor(props) {
    super(props);
    this.state = {
      ws: null,
      data: null
    };
  }

  componentDidMount() {
    this.ws = new WebSocket('ws://localhost:4430/stats');
    this.ws.onopen = () => this.setState({ws: this.ws});
    this.ws.onerror = e => this.setState({ws: null, data: null});
    this.ws.onclose = e => this.setState({ws: null, data: null});
    this.ws.onmessage = e => {
      this.setState({data: JSON.parse(e.data)});
    };
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
    if (!this.state.ws || !this.state.data) {
      return <div className="server">data not available</div>;
    } else {
      return (
        <div>
          <div className="server">
            tunnel server listening on {this.state.data.host}:{' '}
            {this.state.data.port}
          </div>
          <table cellSpacing="0">
            <tbody>{this.connectionRows(this.state.data.connections)}</tbody>
          </table>
        </div>
      );
    }
  }
}

export default App;
