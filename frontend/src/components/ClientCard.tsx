import { 
  AreaChart,
  Area,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip
} from 'recharts'
import { ClientReportData } from '@/types/api'
import { formatCurrency, formatHours } from '@/utils/formatters'

interface ClientCardProps {
  client: ClientReportData
  color?: string
}

// Generate sample daily data for the chart - in real implementation this would come from API
const generateDailyData = (totalHours: number) => {
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
  return days.map((day, index) => ({
    day,
    hours: Math.random() * (totalHours / 5) // Distribute hours randomly across days
  }))
}

export default function ClientCard({ client, color = '#22c55e' }: ClientCardProps) {
  const chartData = generateDailyData(client.total_hours)
  
  return (
    <div className="card">
      <div className="card-body p-6">
        {/* Client Header */}
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-primary mb-1">
            {client.client_name}
          </h3>
        </div>

        {/* Day Graph */}
        <div className="mb-6">
          <div className="h-24 mb-2">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id={`gradient-${client.client_id}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={color} stopOpacity={0.3}/>
                    <stop offset="95%" stopColor={color} stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis 
                  dataKey="day" 
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 10, fill: '#6b7280' }}
                />
                <YAxis hide />
                <Tooltip 
                  formatter={(value) => [formatHours(value as number), 'Hours']}
                  labelStyle={{ color: '#374151' }}
                  contentStyle={{ 
                    backgroundColor: '#ffffff',
                    border: '1px solid #e5e7eb',
                    borderRadius: '8px',
                    fontSize: '12px'
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="hours"
                  stroke={color}
                  strokeWidth={2}
                  fill={`url(#gradient-${client.client_id})`}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Totals Row */}
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <div className="text-sm text-muted mb-1">total hours</div>
            <div className="text-xl font-bold text-primary">
              {formatHours(client.total_hours)}
            </div>
          </div>
          <div>
            <div className="text-sm text-muted mb-1">total earnings</div>
            <div className="text-xl font-bold text-primary">
              {formatCurrency(client.total_earnings_usd || 0, 'USD')}
            </div>
          </div>
        </div>

        {/* Member Breakdown */}
        <div className="space-y-2">
          {client.member_reports.map((member, index) => (
            <div key={member.member_id} className="flex justify-between items-center py-1">
              <div className="text-sm text-secondary">
                {member.member_name}
              </div>
              <div className="flex gap-3 text-sm">
                <span className="text-primary font-medium">
                  {formatHours(member.total_hours)}
                </span>
                <span className="text-success-600 font-medium">
                  {formatCurrency(member.total_earnings_usd || 0, 'USD')}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}