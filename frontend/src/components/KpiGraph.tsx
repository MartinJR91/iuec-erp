import React, { useMemo } from "react";
import { Card, CardContent, Typography, Box } from "@mui/material";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

export interface GraphDataPoint {
  month: string;
  value: number;
}

export interface KpiGraphProps {
  data: GraphDataPoint[];
  title?: string;
  dataKey?: string;
  color?: string;
  height?: number;
}

// Données mock de fallback (6 mois avec valeurs aléatoires)
const generateMockData = (): GraphDataPoint[] => {
  const months = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin"];
  const baseValue = 1000;
  return months.map((month, index) => ({
    month,
    value: baseValue + Math.floor(Math.random() * 300) + index * 50,
  }));
};

const KpiGraph: React.FC<KpiGraphProps> = ({
  data,
  title = "Évolution des données",
  dataKey = "value",
  color = "#1976d2",
  height = 300,
}) => {
  // Utiliser les données fournies ou générer des données mock en fallback
  const chartData = useMemo(() => {
    if (data && data.length > 0) {
      return data;
    }
    return generateMockData();
  }, [data]);

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          {title}
        </Typography>
        <Box sx={{ width: "100%", height, mt: 2 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
              <XAxis
                dataKey="month"
                stroke="#666"
                style={{ fontSize: "12px" }}
              />
              <YAxis
                stroke="#666"
                style={{ fontSize: "12px" }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#fff",
                  border: "1px solid #ccc",
                  borderRadius: "4px",
                }}
              />
              <Legend
                wrapperStyle={{ paddingTop: "20px" }}
              />
              <Line
                type="monotone"
                dataKey={dataKey}
                stroke={color}
                strokeWidth={2}
                dot={{ fill: color, r: 4 }}
                activeDot={{ r: 6 }}
                name="Valeur"
              />
            </LineChart>
          </ResponsiveContainer>
        </Box>
      </CardContent>
    </Card>
  );
};

export default KpiGraph;
