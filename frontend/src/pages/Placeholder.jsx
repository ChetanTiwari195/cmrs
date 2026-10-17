import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export default function Placeholder({ title }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="text-muted-foreground">Nothing here yet.</CardContent>
    </Card>
  )
}
