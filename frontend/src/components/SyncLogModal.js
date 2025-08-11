import React, { useEffect, useRef } from 'react';
import './SyncLogModal.css';

const SyncLogModal = ({ logs, show, onClose }) => {
    const logContentRef = useRef(null);

    // Auto-scroll to the bottom of the log
    useEffect(() => {
        if (logContentRef.current) {
            logContentRef.current.scrollTop = logContentRef.current.scrollHeight;
        }
    }, [logs]);

    if (!show) return null;

    return (
        <div className="sync-log-modal-backdrop">
            <div className="sync-log-modal-content">
                <h3>同步日志</h3>
                <pre ref={logContentRef} className="sync-log-output">
                    {logs.join('\n')}
                </pre>
                <button onClick={onClose} className="close-log-button">关闭</button>
            </div>
        </div>
    );
};

export default SyncLogModal;
