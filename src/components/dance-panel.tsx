import Icon from '../Icon';
import { MOVES, type MoveId } from '../room';
interface Props {
    connected: boolean;
    activeMove: MoveId | null;
    onChoose: (id: MoveId) => void;
}
export default function DancePanel({ connected, activeMove, onChoose }: Props) {
    return (
        <aside className="dance-panel" aria-labelledby="dance-title">
            <p className="panel-kicker">응원 동작</p>
            <h3 id="dance-title">동작 선택</h3>
            <p className="panel-description">
                동작을 선택하면 5초 동안 재생됩니다.{' '}
                {connected
                    ? '연결된 팬들과 함께 볼 수 있습니다.'
                    : '연결 후 다른 팬들과 함께 볼 수 있습니다.'}
            </p>
            <div className="move-list">
                {MOVES.map((move) => (
                    <button
                        type="button"
                        key={move.id}
                        className={`move-button ${activeMove === move.id ? 'is-active' : ''}`}
                        aria-pressed={activeMove === move.id}
                        onClick={() => onChoose(move.id)}
                    >
                        <span className="move-icon">
                            <Icon name={move.icon} />
                        </span>
                        <span>{move.label}</span>
                        <span className="move-arrow">
                            <Icon name="arrow-up-right" />
                        </span>
                    </button>
                ))}
            </div>
        </aside>
    );
}
