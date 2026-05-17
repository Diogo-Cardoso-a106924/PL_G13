program grade
  integer g
  read *, g
  if (g .GE. 18) then
    print *, 'Excelente'
  elseif (g .GE. 14) then
    print *, 'Bom'
  elseif (g .GE. 10) then
    print *, 'Suficiente'
  else
    print *, 'Reprovado'
  endif
end
