import './style.css';
import { attachDebug } from './debug';
import { Game } from './game';
import { bindUI, createUI, showBootError } from './ui';

const root = document.querySelector<HTMLElement>('#app')!;
const canvas = createUI(root);
let game: Game | undefined;
try {
  game = new Game(canvas);
  attachDebug(game);
  bindUI(root, game);
} catch (error) {
  showBootError(root, error);
}

if (import.meta.hot) import.meta.hot.dispose(() => game?.dispose());
