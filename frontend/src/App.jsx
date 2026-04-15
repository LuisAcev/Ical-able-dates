import { Provider } from 'react-redux';
import { store } from './store/store';
import { Canvas } from './layout/Canvas';
import GlobalStyles from '@mui/material/GlobalStyles';

function App() {
  return (
    <Provider store={store}>
      <GlobalStyles styles={{
        '.MuiPickersSectionList-sectionContent[aria-selected="true"]': {
          backgroundColor: 'rgba(22,163,74,0.25) !important',
          borderRadius: '3px',
        },
        '.MuiPickersPopper-root *:focus-visible': {
          outline: 'none !important',
        },
      }} />
      <Canvas />
    </Provider>
  );
}

export default App;
