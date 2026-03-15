import { Provider } from 'react-redux';
import { store } from './store/store';
import { Canvas } from './layout/Canvas';

function App() {
  return (
    <Provider store={store}>
      <Canvas />
    </Provider>
  );
}

export default App;
