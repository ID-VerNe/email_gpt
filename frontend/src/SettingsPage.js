import React, { useState, useEffect } from 'react';
import './SettingsPage.css'; // 稍后创建这个CSS文件

const SettingsPage = ({ onBack }) => {
    const [settings, setSettings] = useState({});
    const [mailboxes, setMailboxes] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [message, setMessage] = useState('');

    const settingLabels = {
        IMAP_SERVER: 'IMAP 服务器',
        IMAP_PORT: 'IMAP 端口',
        IMAP_USERNAME: 'IMAP 用户名',
        IMAP_PASSWORD: 'IMAP 密码',
        MAILBOX: '邮箱',
        FETCH_DAYS_AGO: '获取天数',
        DB_PATH: '数据库路径',
        OPENAI_MODEL: 'OpenAI 模型',
        OPENAI_BASE_URL: 'OpenAI 基础 URL',
    };

    useEffect(() => {
        const fetchInitialData = async () => {
            try {
                setLoading(true);
                // 并行获取设置和邮箱列表
                const [settingsResponse, mailboxesResponse] = await Promise.all([
                    fetch('http://localhost:5001/api/settings'),
                    fetch('http://localhost:5001/api/mailboxes')
                ]);

                if (!settingsResponse.ok) {
                    throw new Error(`获取设置失败! 状态: ${settingsResponse.status}`);
                }
                if (!mailboxesResponse.ok) {
                    throw new Error(`获取邮箱列表失败! 状态: ${mailboxesResponse.status}`);
                }

                const settingsData = await settingsResponse.json();
                const mailboxesData = await mailboxesResponse.json();
                // 将邮箱名字典转换为 [original_name, decoded_name] 的数组形式，方便渲染
                const formattedMailboxes = Object.entries(mailboxesData);

                setSettings(settingsData);
                setMailboxes(formattedMailboxes);

            } catch (e) {
                setError(e.message);
                console.error("获取初始数据失败:", e);
            } finally {
                setLoading(false);
            }
        };
        fetchInitialData();
    }, []);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setSettings(prev => ({ ...prev, [name]: value }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setMessage('');
        try {
            const response = await fetch('http://localhost:5001/api/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(settings),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(`保存失败: ${errorData.message || response.statusText}`);
            }

            const result = await response.json();
            setMessage(result.message || '设置已保存并尝试重启后端服务。');
            alert(result.message || '设置已保存并尝试重启后端服务。');
        } catch (e) {
            setError(e.message);
            console.error("保存设置失败:", e);
            setMessage(`保存失败: ${e.message}`);
        }
    };

    if (loading) return <div className="settings-status">正在加载设置...</div>;
    if (error) return <div className="settings-status error">加载设置失败: {error}</div>;

    return (
        <div className="settings-page">
            <h2>设置</h2>
            <form onSubmit={handleSubmit}>
                {Object.keys(settingLabels).map(key => {
                    if (!settings.hasOwnProperty(key)) return null;

                    return (
                        <div className="form-group" key={key}>
                            <label htmlFor={key}>{settingLabels[key]}:</label>
                            {key === 'MAILBOX' ? (
                                <select
                                    id={key}
                                    name={key}
                                    value={settings[key] || ''}
                                    onChange={handleChange}
                                >
                                    <option value="">选择一个邮箱</option>
                                    {mailboxes.map(([originalName, decodedName]) => (
                                        <option key={originalName} value={originalName}>{decodedName}</option>
                                    ))}
                                </select>
                            ) : (
                                <input
                                    type={key.includes('PASSWORD') ? 'password' : 'text'}
                                    id={key}
                                    name={key}
                                    value={settings[key] || ''}
                                    onChange={handleChange}
                                />
                            )}
                        </div>
                    );
                })}
                <div style={{ textAlign: 'center' }}>
                    <button type="submit" className="save-button">保存设置</button>
                    <button type="button" onClick={onBack} className="back-button">返回收件箱</button>
                </div>
            </form>
            {message && <p className={`settings-message ${error ? 'error' : ''}`}>{message}</p>}
        </div>
    );
};

export default SettingsPage;
