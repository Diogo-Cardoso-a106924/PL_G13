program nestedif
  integer x, y
  read *, x
  read *, y
  if (x .GT. 0) then
    if (y .GT. 0) then
      print *, 'ambos positivos'
    else
      print *, 'x positivo, y nao'
    endif
  else
    print *, 'x nao positivo'
  endif
end
