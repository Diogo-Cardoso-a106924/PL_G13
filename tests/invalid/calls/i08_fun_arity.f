program badfunarity
  integer r
  r = double(1, 2)
  print *, r
end

integer function double(x)
  integer x
  double = x * 2
  return
end
