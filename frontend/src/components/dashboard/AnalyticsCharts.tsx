
import React from 'react';
import {
    AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    PieChart, Pie, Cell, Legend
} from 'recharts';
import { Card } from '../common';

// Types (to be moved to types/index.ts usually, but inline for speed here)
interface HistoryPoint {
    date: string;
    total_value: number;
    invested: number;
    cash: number;
}

interface BrokerBreakdown {
    broker_name: string;
    total: number;
    cash: number;
    invested: number;
}

interface AnalyticsChartsProps {
    history: HistoryPoint[];
    breakdown: BrokerBreakdown[];
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

export const AnalyticsCharts: React.FC<AnalyticsChartsProps> = ({ history, breakdown }) => {

    // Format dates for XAxis
    const formattedHistory = history.map(item => ({
        ...item,
        formattedDate: new Date(item.date).toLocaleDateString(undefined, { day: '2-digit', month: '2-digit' })
    }));

    return (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '24px', marginBottom: '24px' }}>
            {/* Evolution Graph */}
            <div style={{ height: '100%' }}>
                <Card className="h-full">
                    <div style={{ padding: '20px', minHeight: '400px' }}>
                        <h3 style={{ marginBottom: '20px', fontSize: '1.1rem', fontWeight: 600 }}>Évolution du Portefeuille</h3>
                        <div style={{ width: '100%', height: 300 }}>
                            <ResponsiveContainer>
                                <AreaChart data={formattedHistory}>
                                    <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
                                    <XAxis
                                        dataKey="formattedDate"
                                        tick={{ fill: '#888' }}
                                        tickLine={false}
                                    />
                                    <YAxis
                                        tick={{ fill: '#888' }}
                                        tickLine={false}
                                        tickFormatter={(val) => `${(val / 1000).toFixed(0)}k`}
                                    />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#1a1a1a', border: '1px solid #333' }}
                                        itemStyle={{ color: '#fff' }}
                                        formatter={(value: number) => [`${value.toFixed(2)} €`, '']}
                                    />
                                    <Area
                                        type="monotone"
                                        dataKey="total_value"
                                        stroke="#8884d8"
                                        fill="#8884d8"
                                        fillOpacity={0.2}
                                        name="Valeur Totale"
                                    />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                </Card>
            </div>

            {/* Allocation Pie Chart */}
            <div style={{ height: '100%' }}>
                <Card className="h-full">
                    <div style={{ padding: '20px', minHeight: '400px' }}>
                        <h3 style={{ marginBottom: '20px', fontSize: '1.1rem', fontWeight: 600 }}>Répartition par Broker</h3>
                        <div style={{ width: '100%', height: 300 }}>
                            <ResponsiveContainer>
                                <PieChart>
                                    <Pie
                                        data={breakdown}
                                        dataKey="total"
                                        nameKey="broker_name"
                                        cx="50%"
                                        cy="50%"
                                        outerRadius={100}
                                        fill="#8884d8"
                                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                                    >
                                        {breakdown.map((entry, index) => (
                                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                        ))}
                                    </Pie>
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#1a1a1a', border: '1px solid #333' }}
                                        formatter={(value: number) => [`${value.toFixed(2)} €`, '']}
                                    />
                                    <Legend verticalAlign="bottom" height={36} />
                                </PieChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                </Card>
            </div>
        </div>
    );
};
